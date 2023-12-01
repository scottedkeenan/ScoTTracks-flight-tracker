import configparser
import json
import logging
import os
import pprint
import traceback

import pika
from pika.exceptions import StreamLostError

import sys

from mysql.connector import pooling

from ogn.parser import ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, \
    get_airfields_for_countries, get_device_data_by_address

from datetime import datetime

from geopy import distance as measure_distance

from scipy.spatial import kdtree

import flight_processor
import aerotow_processor

from charts import json_datetime_converter

from statistics import mean, StatisticsError

from ogn_ddb import import_device_data

from repository.dict.flight_repository_dict import FlightRepositoryDict
from repository.redis.flight_repository_redis import FlightRepositoryRedis

from repository.dict.aerotow_repository_dict import AerotowRepositoryDict
from repository.redis.aerotow_repository_redis import AerotowRepositoryRedis

config = configparser.ConfigParser()
config.read('config.ini')

# Queue connection for saving beacons
mq_connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host'], heartbeat=0))
mq_channel = mq_connection.channel()


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_beacon_correction_data():
    try:
        with open('beacon-correction-data.json', 'r') as beacon_correction_data:
            return json.loads(beacon_correction_data.read())
    except FileNotFoundError:
        log.error('No ogn beacon correction file found')
        return {}


log.info('Importing beacon corrections')
BEACON_CORRECTIONS = import_beacon_correction_data()

log.info(pprint.pformat(BEACON_CORRECTIONS))

tracked_aircraft_repository = FlightRepositoryRedis(config)
# tracked_aircraft_repository = FlightRepositoryDict()
aerotow_repository = AerotowRepositoryRedis(config)
# aerotow_repository = AerotowRepositoryDict()

connection_pool = pooling.MySQLConnectionPool(pool_name="pynative_pool",
                                              pool_size=5,
                                              pool_reset_session=True,
                                              host=config['TRACKER']['database_host'],
                                              database=config['TRACKER']['database'],
                                              user=config['TRACKER']['database_user'],
                                              password=config['TRACKER']['database_password'],
                                              port=config['TRACKER']['database_port'],
                                              ssl_disabled=True if config['TRACKER']['database_ssl_disabled'] == 'True' else False
                                              )


def make_database_connection():
    connection_object = connection_pool.get_connection()
    if connection_object.is_connected():
        return connection_object


db_conn = make_database_connection()

log.info('Importing device data')
# import_device_data(db_conn, config['TRACKER']['device_data_url'])

AIRFIELD_DATA = {}
for airfield in get_airfields_for_countries(db_conn.cursor(dictionary=True),
                                            config['TRACKER']['track_countries'].split(',')):
    airfield_json = {
        'id': airfield['id'],
        'name': airfield['name'],
        'nice_name': airfield['nice_name'] if airfield['nice_name'] else airfield['name'],
        'latitude': airfield['latitude'],
        'longitude': airfield['longitude'],
        'elevation': airfield['elevation'],
        'launch_type_detection': True if airfield['launch_type_detection'] == 1 else False,
        'follow_aircraft': True if airfield['follow_aircraft'] == 1 else False
    }
    AIRFIELD_DATA[(airfield_json['latitude'], airfield_json['longitude'])] = airfield_json

AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
log.debug('Airfields loaded: {}'.format(pprint.pformat(AIRFIELD_LOCATIONS)))
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)

db_conn.close()


def detect_airfield(beacon, flight):
    """
    :param beacon: The beacon data containing the gps position to make the detection from
    :param flight: The flight dict the beacon relates to
    :return:
    """
    detection_radius = float(config['TRACKER']['airfield_detection_radius'])

    # If flight is still near the same airfield, do nothing
    if flight['nearest_airfield'] and flight['distance_to_nearest_airfield']:
        current_distance_to_airfield = measure_distance.distance(
            [float(flight['nearest_airfield']['latitude']), float(flight['nearest_airfield']['longitude'])],
            (beacon['latitude'], beacon['longitude'])).km
        if current_distance_to_airfield <= detection_radius:
            flight['distance_to_nearest_airfield'] = current_distance_to_airfield
            return

    # If not, detect the nearest airfield and update the flight
    _, closest_airfield_index = AIRFIELD_TREE.query((float(beacon['latitude']), float(beacon['longitude'])), 1)
    closest_airfield = AIRFIELD_DATA[AIRFIELD_LOCATIONS[closest_airfield_index]]
    distance_to_nearest = measure_distance.distance(
        [float(closest_airfield['latitude']), float(closest_airfield['longitude'])],
        (beacon['latitude'], beacon['longitude'])).km
    log.debug(("nearest is: {} at {}".format(closest_airfield['name'], distance_to_nearest)))
    flight['nearest_airfield'] = closest_airfield
    flight['distance_to_nearest_airfield'] = distance_to_nearest


def detect_tug(tracked_aircraft, flight):
    log.debug('Looking for a tug launch for {}'.format(flight['registration']))
    if flight['aircraft_type'] == 2:
        log.info('This IS a tug!')
        return False
    for other_flight_address, other_flight in tracked_aircraft.get_all_flights().items():
        if other_flight_address == flight['address']:
            continue
        if other_flight['takeoff_timestamp'] and other_flight['takeoff_airfield'] == flight['takeoff_airfield']:
            time_difference = (other_flight['takeoff_timestamp'] - flight['takeoff_timestamp']).total_seconds()
            if -10 < time_difference < 10:
                if other_flight['aircraft_type'] == 2:
                    log.info("Tug found: {} is towing {} at {}".format(
                        other_flight['address'] if other_flight['registration'] == 'UNKNOWN' else other_flight['registration'],
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['nearest_airfield']['name']))
                    flight['launch_type'] = 'aerotow_glider'
                    other_flight['launch_type'] = 'aerotow_tug'

                else:
                    log.info(
                        "Aerotow pair found, can't tell which is the tug though: {} is towing with {} at {}".format(
                            other_flight['address'] if other_flight['registration'] == 'UNKNOWN' else other_flight['registration'],
                            flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                            flight['nearest_airfield']['name']))
                    flight['launch_type'] = 'aerotow_pair'
                    other_flight['launch_type'] = 'aerotow_pair'
                aerotow = aerotow_processor.new_aerotow(flight, other_flight)
                aerotow_key = aerotow_repository.add_aerotow(aerotow)
                if aerotow_key:
                    flight['tug'] = other_flight['address']
                    flight['at_partner_registration'] = other_flight['registration'] if other_flight['registration'] else other_flight['address']
                    flight['aerotow_key'] = aerotow_key
                    other_flight['tug'] = flight['address']
                    other_flight['at_partner_registration'] = flight['registration'] if flight['registration'] else flight['address']
                    other_flight['aerotow_key'] = aerotow_key

                    tracked_aircraft.update_flight(flight)
                    tracked_aircraft.update_flight(other_flight)
                    return True

def save_beacon(body, flight):
    # Types:
    # 'all': Save all beacons
    # 'aircraft': Save beacons of selected aircraft (TODO)
    # 'airfield': Save beacons of selected airfields
    # False: No saving of beacons

    config_save_beacon = config['TRACKER']['save_beacon']

    if config_save_beacon == 'False':
        log.debug('Not Saving beacon for {}'.format(flight['registration'] if flight['registration'] else flight['address']))

    # We want to save all beacons
    if config_save_beacon == 'all':
        log.debug(
            'Saving beacon (all) for {} at {}.'.format(
                flight['registration'] if flight['registration'] else flight['address'],
                flight['takeoff_airfield'] if flight['takeoff_airfield'] else flight['nearest_airfield'],
            ))
        mq_channel.basic_publish(exchange='flight_tracker',
                                 routing_key='beacons_to_save',
                                 body=body)
    # We want to save all beacons from a specific aircraft
    if config_save_beacon == 'aircraft':
        log.warning('Saving beacon (aircraft) for {}'.format(flight['registration'] if flight['registration'] else flight['address']))
        log.warning('Not implemented!')

    # We want to save all beacons from this airfield
    if config_save_beacon == 'airfield':
        try:
            takeoff_airfield_follows = flight['takeoff_airfield']['follow_aircraft']
        except TypeError:
            takeoff_airfield_follows = False
        try:
            nearest_airfield_follows = flight['nearest_airfield']['follow_aircraft']
        except TypeError:
            nearest_airfield_follows = False
        if takeoff_airfield_follows or nearest_airfield_follows:
            log.debug(
                'Saving beacon (airfield) for {} at {}. Nearest: {} Takeoff: {}'.format(
                    flight['registration'] if flight['registration'] else flight['address'],
                    flight['takeoff_airfield'] if flight['takeoff_airfield'] else flight['nearest_airfield'],
                    nearest_airfield_follows,
                    takeoff_airfield_follows
                ))
            mq_channel.basic_publish(exchange='flight_tracker',
                                     routing_key='beacons_to_save',
                                     body=body)


def track_aircraft(beacon, body, check_date=True):
    try:
        reference_timestamp = datetime.fromisoformat(beacon['reference_timestamp'])
    except ValueError:
        reference_timestamp = datetime.fromisoformat(beacon['reference_timestamp'])
    beacon['reference_timestamp'] = reference_timestamp

    timestamp = datetime.fromisoformat(beacon['timestamp'])
    beacon['timestamp'] = timestamp

    try:
        beacon['altitude'] = beacon['altitude'] + BEACON_CORRECTIONS[beacon['receiver_name']]
        log.debug('Correction applied for {} beacon. Alt: {}'.format(beacon['receiver_name'], beacon['altitude']))
    except KeyError:
        # log.info('No correction to apply for {} beacon. Alt: {}'.format(beacon['receiver_name'], beacon['altitude']))
        pass

    flight_exists = tracked_aircraft_repository.address_exists(beacon['address'])
    if flight_exists and check_date:
        # Remove outdated tracking
        # Todo: consider removal
        if datetime.date(tracked_aircraft_repository.get_flight(beacon['address'])['timestamp']) < datetime.utcnow().date():
            tracked_aircraft_repository.delete_flight(beacon['address'])
            log.debug("Removed outdated tracking for: {}".format(beacon['address']))
        else:
            log.debug('Tracking checked and is up to date')

    if not flight_exists:
        try:
            db_conn = make_database_connection()
            device = get_device_data_by_address(db_conn.cursor(dictionary=True), beacon['address'])
            db_conn.close()
        except KeyError:
            log.error('Device dict not found for {}'.format(beacon['address']))
            device = None

        if device:
            log.info('Using data in device database')
            log.info(device)

            if device['identified'] == 1:
                registration = device['registration'].upper() if device['registration'] else 'UNKNOWN'
            else:
                log.info('Aircraft {} requests no identify'.format(beacon['address']))
                if device['registration'] != '':
                    log.info("Don't identify but reg included: {}!".format(device['registration']))
                registration = 'UNKNOWN'
            aircraft_model = device['aircraft_model'] if device['aircraft_model'] else None
            competition_number = device['cn'] if device['cn'] else None

            if device['tracked'] != 1:
                log.warning('Aircraft {}/{} requests no track'.format(registration, beacon['address']))

                no_track_flight = flight_processor.new_flight()
                no_track_flight.update({
                    'nearest_airfield': None,
                    'address': beacon['address'],
                    'aircraft_type': 'no_track',
                    'altitude': None,
                    'ground_speed': None,
                    'receiver_name': None,
                    'timestamp': None,
                    'registration': None,
                    'aircraft_model': None,
                    'competition_number': None
                })
                no_track_flight['timestamp'] = beacon['timestamp'].replace(hour=0, minute=0, second=0)
                tracked_aircraft_repository.add_flight(beacon['address'], no_track_flight)
                return
        else:
            log.info('Setting device data to unknowns')
            registration = 'UNKNOWN'
            aircraft_model = None
            competition_number = None

        log.info('Aircraft {}/{} not tracked yet'.format(registration, beacon['address']))

        new_flight = flight_processor.new_flight()
        new_flight.update({
            'nearest_airfield': None,
            'address': beacon['address'],
            'aircraft_type': beacon['aircraft_type'],
            'altitude': beacon['altitude'],
            'ground_speed': beacon['ground_speed'],
            'receiver_name': beacon['receiver_name'],
            'timestamp': timestamp,
            'registration': registration,
            'aircraft_model': aircraft_model,
            'competition_number': competition_number
        })

        detect_airfield(beacon, new_flight)

        if beacon['ground_speed'] > config.getfloat('TRACKER', 'airborne_detection_speed') and flight_processor.height_agl(new_flight) > config.getfloat('TRACKER', 'airborne_detection_agl'):
            new_flight['status'] = 'air'
            log.info('Checking if this detection can be treated as a launch')

            # if low enough and near enough, treat as a launch
            # Todo: set landing estimate too - when an aircraft is detected for the first time in a while, check if its last beacon looked like a landing

            # Strictly reject if timedelta is too large
            beacon_delta = (beacon['reference_timestamp'] - beacon['timestamp']).total_seconds()
            log.info("beacon delta: {} seconds. Timestamps: ts: {} rts: {}".format(beacon_delta, beacon['timestamp'], beacon['reference_timestamp']))
            if beacon_delta > config.getfloat('TRACKER', 'first_in_air_detection_time_delta') or beacon_delta < 0:
                log.info('Bad beacon delta {}, not treating as a launch'.format(beacon_delta))
            else:
                if new_flight['distance_to_nearest_airfield'] < config.getfloat('TRACKER', 'first_in_air_detection_radius')\
                        and flight_processor.height_agl(new_flight) < config.getfloat('TRACKER', 'first_in_air_detection_agl'):
                    log.info("Adding aircraft {} as launched at {} @ {} [First detection in air]".format(
                        new_flight['address'] if new_flight['registration'] == 'UNKNOWN' else new_flight['registration'],
                        new_flight['nearest_airfield']['name'],
                        new_flight['timestamp']
                    ))
                    flight_processor.launch(new_flight, tracked_aircraft_repository)
                    db_conn = make_database_connection()
                    add_flight(db_conn.cursor(), new_flight)
                    db_conn.commit()
                    db_conn.close()
        else:
            new_flight['status'] = 'ground'
        log.info("Starting to track aircraft {}/{} {}km from {} with status {}".format(registration,
                                                                                       new_flight['address'],
                                                                                       new_flight['distance_to_nearest_airfield'],
                                                                                       new_flight['nearest_airfield'][
                                                                                           'name'],
                                                                                       new_flight['status']))
        log.info("Extra detail for {}/{}: Model: {}, CN: {}".format(registration,
                                                                    new_flight['address'],
                                                                    aircraft_model,
                                                                    competition_number))

        log.info("Ground speed: {} | Alt: {} | time: {}".format(beacon['ground_speed'], beacon['altitude'],
                                                                beacon['timestamp']))

        tracked_aircraft_repository.add_flight(beacon['address'], new_flight)
        save_beacon(body, new_flight)
    else:
        log.debug('Updating tracked aircraft')
        flight = tracked_aircraft_repository.get_flight(beacon['address'])
        if flight['aircraft_type'] == 'no_track':
            return

        save_beacon(body, flight)

        if beacon['timestamp'] <= flight['timestamp']:
            # log.info('Skipping beacon from the past')
            # log.info(f"{flight['registration']} Beacon {beacon['timestamp']}, flight {flight['timestamp']}, rec {beacon['receiver_name']}")
            return

        # update fields of flight
        detect_airfield(beacon, flight)  # updates airfield and distance to airfield
        last_flight_timestamp = flight['timestamp']
        flight_processor.update(flight, tracked_aircraft_repository, beacon)

        if flight['status'] == 'ground' and last_flight_timestamp <= timestamp:

            if beacon['ground_speed'] > float(config['TRACKER']['airborne_detection_speed']) \
                    and flight_processor.height_agl(flight) > float(config['TRACKER']['airborne_detection_agl']):

                # Aircraft launch detected
                # At airfield
                if flight['distance_to_nearest_airfield'] < float(config['TRACKER']['airfield_detection_radius']):
                    log.info("Adding aircraft {} as launched at {} @ {} [at airfield] ref: [{}]".format(
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['nearest_airfield']['name'],
                        beacon['timestamp'],
                        beacon['reference_timestamp']))
                    flight_processor.launch(flight, tracked_aircraft_repository)
                    db_conn = make_database_connection()
                    add_flight(db_conn.cursor(), flight)
                    db_conn.commit()
                    db_conn.close()
                # 2.5 nautical miles
                elif flight['distance_to_nearest_airfield'] < 4.63:
                    # todo: give airfields a max launch detection range
                    # Not near airfield anymore - tracking for launch has been missed
                    log.info("Adding aircraft {} as launched at {} but we missed it".format(
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['nearest_airfield']['name'],
                        flight['timestamp']))
                    # todo: use the time known arg below to srt flag in db
                    flight_processor.launch(flight, tracked_aircraft_repository)
                    # todo: enum/dict the launch types 1: etc.
                    flight['launch_type'] = 'unknown, nearest field'
                    # prevent launch height tracking
                    flight['launch_height'] = None
                    flight['launch_complete'] = True
                    db_conn = make_database_connection()
                    add_flight(db_conn.cursor(), flight)

                    db_conn.commit()
                    db_conn.close()
                # 2.5 nautical miles
                elif flight['distance_to_nearest_airfield'] < 10:
                    # todo: give airfields a max launch detection range
                    # Not near airfield at all
                    log.info("Adding aircraft {} as launched near(ish) {} but outside 2.5 nautical mile radius".format(
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['nearest_airfield']['name'],
                        flight['timestamp']))

                    flight_processor.launch(flight, tracked_aircraft_repository, time_known=False)

                    # todo: use the time known arg below to srt flag in db
                    # todo: enum/dict the launch types 1:winch etc.
                    flight['launch_type'] = 'unknown, {}km'.format(round(flight['distance_to_nearest_airfield'], 2))

                    # prevent launch height tracking
                    flight['takeoff_airfield'] = 'UNKNOWN'
                    flight['launch_height'] = None
                    flight['launch_complete'] = True

                    db_conn = make_database_connection()
                    add_flight(db_conn.cursor(), flight)

                    db_conn.commit()
                    db_conn.close()

        elif flight['status'] == 'air':
            # log.info('Speed: {}, {} | AGL: {}, {} | Dist: {} {} | Climb: {} {}'.format(
            #     beacon['ground_speed'], beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed']),
            #     flight.agl(), flight.agl() < float(config['TRACKER']['landing_detection_agl']),
            #     flight.distance_to_nearest_airfield, flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius']),
            #     beacon['climb_rate'], beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate'])))

            # todo remove unused flight object fields eg 'tracking_launch_height'

            if flight['takeoff_timestamp'] and not flight['launch_complete'] and last_flight_timestamp <= timestamp:

                time_since_launch = flight_processor.seconds_since_launch(flight)
                log.debug("time since launch: {}".format(time_since_launch))

                # todo config

                launch_tracking_times = {
                    'winch': 60,
                    'max': 1000
                }

                if time_since_launch <= launch_tracking_times['max']:
                    # log.info("Updating aircraft {} launch height".format(flight.registration))
                    # log.info("{} launch height is: {}".format(flight.registration, flight.launch_height))
                    # log.info("{} launch vertical speed is {}".format(flight.registration, beacon['climb_rate']))
                    # log.info("{} launch type is {}".format(flight.registration, flight.launch_type))

                    if beacon['climb_rate'] > flight['max_launch_climb_rate']:
                        flight['max_launch_climb_rate'] = beacon['climb_rate']

                    if not flight['launch_type']:
                        # detect tug will update the launch type if a flarm tug is detected
                        if not detect_tug(tracked_aircraft_repository, flight):
                            log.debug(
                                f"{flight['registration']} launch beacon heights {len(flight['launch_beacon_heights'])}")
                            if len(flight['launch_beacon_heights']) >= 5:
                                log.debug('Deciding launch type for {} at {} @{} based on gradient: {}[{}]'.format(
                                    flight['registration'],
                                    flight['nearest_airfield']['name'],
                                    flight['takeoff_timestamp'],
                                    flight_processor.launch_gradient(flight),
                                    beacon['receiver_name']
                                ))
                                if flight_processor.launch_gradient(flight) > float(
                                        config['TRACKER']['winch_detection_gradient']):
                                    log.info('{} detected winch launching at {}'.format(flight['registration'],
                                                                                        flight['nearest_airfield'][
                                                                                            'name']))
                                    flight_processor.set_launch_type(flight, tracked_aircraft_repository, 'winch')
                                elif len(flight['launch_beacon_heights']) >= 10:
                                    try:
                                        flight['average_launch_climb_rate'] = mean(
                                            flight['launch_climb_rates'].values())
                                    except StatisticsError:
                                        log.info("No data to average, skipping")
                                log.info('{} detected aerotow (unknown tug) or self launching at {}'.format(
                                    flight['registration'], flight['nearest_airfield']['name']))
                                flight_processor.set_launch_type(flight, tracked_aircraft_repository, 'aerotow_sl')
                elif not flight['launch_complete']:
                    flight['launch_complete'] = True
                    log.info(
                        '{} launch complete (timeout) at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}'.format(
                            flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                            flight['nearest_airfield']['name'],
                            flight['launch_type'],
                            flight['launch_height'] * 3.281,
                            time_since_launch,
                            flight['average_launch_climb_rate']

                        ))
                    db_conn = make_database_connection()
                    update_flight(db_conn.cursor(), flight)
                    db_conn.commit()
                    db_conn.close()

                if flight['launch_type'] == 'winch' and time_since_launch > launch_tracking_times['winch']:
                    flight['launch_complete'] = True
                    log.info(
                        '{} winch launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}'.format(
                            flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                            flight['nearest_airfield']['name'],
                            flight['launch_type'],
                            flight['launch_height'] * 3.281,
                            time_since_launch,
                            flight['average_launch_climb_rate']
                        )
                    )
                    # log.info('Launch gradients: {}'.format(flight['launch_gradients']))
                    db_conn = make_database_connection()
                    update_flight(db_conn.cursor(), flight)
                    db_conn.commit()
                    db_conn.close()

                if flight['launch_type'] in ['aerotow_glider', 'aerotow_pair', 'aerotow_tug']:
                    try:
                        flight_processor.update_aerotow(flight, beacon, tracked_aircraft_repository, aerotow_repository)
                    except AttributeError as err:
                        log.error(err)
                        log.error(
                            'Something went wrong with aerotow update for {}/{}, aborting'.format(flight['registration'],
                                                                                                  flight['address']))
                        aerotow_data = aerotow_repository.get_aerotow(flight['aerotow_key'])
                        aerotow_processor.abort(flight, aerotow_data, aerotow_repository, tracked_aircraft_repository)

                if flight['launch_type'] in ['aerotow_sl', 'tug']:
                    try:
                        recent_average = mean(list(flight['launch_climb_rates'].values())[-10:])
                        recent_average_diff = recent_average - flight['average_launch_climb_rate']

                        if recent_average_diff < -2 or recent_average_diff > 5:
                            sl = None
                            if recent_average_diff < -2:
                                sl = "sink"
                            if recent_average_diff > 2:
                                sl = "lift"
                            flight['launch_complete'] = True
                            log.debug(flight['launch_climb_rates'].values())
                            log.info(
                                '{} {} launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}, Recent Average Vertical: {}, Difference: {}, Sink/lift: {}'.format(
                                    flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                                    flight['launch_type'],
                                    flight['nearest_airfield']['name'],
                                    flight['launch_type'],
                                    flight['launch_height'] * 3.281,
                                    time_since_launch,
                                    flight['average_launch_climb_rate'],
                                    recent_average,
                                    recent_average_diff,
                                    sl
                                )
                            )
                            db_conn = make_database_connection()
                            update_flight(db_conn.cursor(), flight)
                            db_conn.commit()
                            db_conn.close()
                    except StatisticsError:
                        log.info("No data to average, skipping")

            if flight['status'] == 'air' \
                    and beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed']) \
                    and flight_processor.height_agl(flight) < float(config['TRACKER']['landing_detection_agl']) \
                    and flight['distance_to_nearest_airfield'] < float(config['TRACKER']['airfield_detection_radius']) \
                    and beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate']):

                log.info("Aircraft {} detected below airborne detection criteria".format(
                    flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration']))

                if last_flight_timestamp <= timestamp:
                    # Aircraft landing detected
                    flight['status'] = 'ground'
                    flight['landing_timestamp'] = timestamp
                    flight['landing_airfield'] = flight['nearest_airfield']['id']

                    if flight['takeoff_timestamp'] and not flight['launch_complete']:
                        if flight['launch_type'] in ['aerotow_glider', 'aerotow_pair', 'aerotow_tug']:
                            aerotow_data = aerotow_repository.get_aerotow(flight['aerotow_key'])
                            aerotow_processor.abort(flight, aerotow_data, aerotow_repository, tracked_aircraft_repository)
                            log.info('Aerotow {} aborted because aircraft {} landed'.format(flight['aerotow_key'], flight['address']))
                        # flight['launch_type'] = 'winch l/f'

                    log.info("Updating aircraft {} as landed at {} @ {} Ref:[{}]".format(
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['nearest_airfield']['name'],
                        flight['landing_timestamp'],
                        beacon['reference_timestamp']))

                    log.info('Landing data... ground_speed: {}, agl: {}, climb_rate: {}'.format(
                        beacon['ground_speed'],
                        flight_processor.height_agl(flight),
                        beacon['climb_rate']))
                    db_conn = make_database_connection()
                    if flight['takeoff_timestamp']:
                        update_flight(db_conn.cursor(),flight)
                        db_conn.commit()
                    else:
                        add_flight(db_conn.cursor(), flight)
                        db_conn.commit()

                    log.info('Aircraft {} flew from {} to {}'.format(
                        flight['address'] if flight['registration'] == 'UNKNOWN' else flight['registration'],
                        flight['takeoff_timestamp'],
                        flight['landing_timestamp']))

                    log.debug('ALT GRAPH? ' + config['TRACKER']['draw_alt_graph'])
                    if config['TRACKER']['draw_alt_graph'] == 'true' and flight['takeoff_timestamp'] and flight['landing_timestamp']:
                        chart_payload = {
                            'takeoff_timestamp': flight['takeoff_timestamp'],
                            'landing_timestamp': flight['landing_timestamp'],
                            'address': flight['address']
                        }
                        try:
                            mq_channel.basic_publish(exchange='flight_tracker',
                                                     routing_key='charts_to_draw',
                                                     body=json.dumps(
                                                         chart_payload,
                                                         default=json_datetime_converter
                                                     ).encode())
                        except TypeError as e:
                            print(e)
                            raise e

                    flight_processor.reset(flight, tracked_aircraft_repository)
                    db_conn.close()
        tracked_aircraft_repository.update_flight(flight, flight['address'])


beacon_count = 0
check_date = True if config['TRACKER']['check_date'] == 'True' else False


def process_beacon(ch, method, properties, body):
    try:
        beacon = json.loads(body)
        try:
            log.debug('Aircraft beacon received')
            try:
                track_aircraft(beacon, body, check_date)
            except TypeError as e:
                log.error('Type error while tracking: {}'.format(e))
                raise
            except configparser.NoOptionError as e:
                log.error('Config error while tracking: {}'.format(e))
            except KeyError as e:
                log.error('Key error while tracking {}'.format(e))
                log.error('Key error while tracking {}'.format(traceback.print_exc()))
        except KeyError as e:
            log.debug('Beacon type field not found: {}'.format(e))
    except ParseError as e:
        log.error('Parse error: {}'.format(e))


db_conn = make_database_connection()

log.info("Checking database for active flights")
if db_conn:
    database_flights = get_currently_airborne_flights(db_conn.cursor(dictionary=True))
else:
    log.error('Unable to retrieve database flights')
    database_flights = {}

for db_flight in database_flights:
    db_tracked_flight = flight_processor.new_flight()
    db_tracked_flight.update(
        {
            'nearest_airfield': db_flight['airfield'],
            'address': db_flight['address'],
            'aircraft_type': db_flight['aircraft_type'],
            'altitude': db_flight['altitude'],
            'ground_speed': db_flight['ground_speed'],
            'receiver_name': db_flight['receiver_name'],
            'timestamp': db_flight['reference_timestamp'],
            'registration': db_flight['registration'],
            'aircraft_model': db_flight['aircraft_model'],
            'competition_number': db_flight['competition_number'],
            'takeoff_timestamp': db_flight['takeoff_timestamp'],
            'landing_timestamp': db_flight['landing_timestamp'],
            'status': db_flight['status'],
            'tracking_launch_height': db_flight['tracking_launch_height'],
            'tracking_launch_start_time': db_flight['tracking_launch_start_time'],
            'launch_height': db_flight['launch_height'],
            'takeoff_airfield': db_flight['takeoff_airfield'],
            'landing_airfield': db_flight['landing_airfield'],
            'launch_type': db_flight['launch_type'],
            'average_launch_climb_rate': db_flight['average_launch_climb_rate'],
            'max_launch_climb_rate': db_flight['max_launch_climb_rate'],
            'launch_complete': True if db_flight['launch_complete'] == 1 else False,
            'tug': db_flight['tug_registration']
        }
    )

    tracked_aircraft_repository.add_flight(db_tracked_flight['address'], db_tracked_flight)

log.info("Cached flights =========")
for aircraft_address in tracked_aircraft_repository.get_all_addresses():
    log.info(pprint.pformat(tracked_aircraft_repository.get_flight(aircraft_address)))
log.info("=========")


def connect_to_queue():
    connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host'], heartbeat=0))
    channel = connection.channel()

    # channel.basic_consume(queue='received_beacons',
    channel.basic_consume(queue='received_beacons',
                          auto_ack=True,
                          on_message_callback=process_beacon)

    channel.start_consuming()


def main():
    while True:
        try:
            connect_to_queue()
        except pika.exceptions.StreamLostError:
            log.error('Queue connection lost, retrying')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        db_conn.close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
