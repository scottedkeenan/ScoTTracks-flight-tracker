import configparser
import requests
import json
import logging
import os
import pprint

import pika

import sys

import mysql.connector

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between, get_raw_beacons_between, get_airfields, get_filters_by_country_codes, get_airfields_for_countries, get_raw_beacons_for_address_between

from charts import draw_alt_graph

from datetime import datetime

from geopy import distance as measure_distance

from scipy.spatial import kdtree

from flight import Flight

from aerotow import Aerotow

from statistics import mean, StatisticsError


config = configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_device_data():

    # todo: import to database?
    # todo: keep file for reference?

    # "4054A1": {
    #     "DEVICE_TYPE": "I",
    #     "DEVICE_ID": "4054A1",
    #     "AIRCRAFT_MODEL": "ASK-21",
    #     "REGISTRATION": "G-CHPW",
    #     "CN": "HPW",
    #     "TRACKED": "Y",
    #     "IDENTIFIED": "Y"
    # }

    r = requests.get(config['TRACKER']['device_data_url'])

    if r.status_code != 200:
        log.error('Unable to update device dict: code {}'.format(r.status_code))
        try:
            with open('ogn-ddb.json', 'r') as ddb_data:
                return json.loads(ddb_data.read())
        except FileNotFoundError:
            log.error('No ogn ddb file found')
            return {}

    device_data = r.text

    keys = []
    device_dict = {}

    for line in device_data.splitlines():
        if line[0] == '#':
            keys = line[1:].split(',')
        else:
            values = line.split(',')
            device = {keys[i].strip("'"): values[i].strip("'") for i,key in enumerate(keys)}
            device_dict[device['DEVICE_ID']] = device

    with open('ogn-ddb.json', 'w') as ddb_data:
        ddb_data.write(json.dumps(device_dict))

    return device_dict


def import_beacon_correction_data():
    try:
        with open('beacon-correction-data.json', 'r') as beacon_correction_data:
            return json.loads(beacon_correction_data.read())
    except FileNotFoundError:
        log.error('No ogn beacon correction file found')
        return {}


log.info('Importing device data')
DEVICE_DICT = import_device_data()

log.info('Importing beacon corrections')
BEACON_CORRECTIONS = import_beacon_correction_data()

log.info(pprint.pformat(BEACON_CORRECTIONS))

tracked_aircraft = {}


def make_database_connection(retry_counter=0):
    if retry_counter > 5:
        log.error("Failed to connect to database after 5 retries")
        return
    try:
        conn = mysql.connector.connect(
            user=config['TRACKER']['database_user'],
            password=config['TRACKER']['database_password'],
            host=config['TRACKER']['database_host'],
            database=config['TRACKER']['database'])
        return conn
    except mysql.connector.Error as err:
        log.error(err)
        retry_counter += 1
        return make_database_connection(retry_counter)


db_conn = make_database_connection()
if not db_conn:
    exit(1)

AIRFIELD_DATA = {}
for airfield in get_airfields_for_countries(db_conn.cursor(), config['TRACKER']['track_countries'].split(',')):
    airfield_json = {
        'id': airfield[0],
        'name': airfield[1],
        'nice_name': airfield[11] if airfield[11] else airfield[1],
        'latitude': airfield[4],
        'longitude': airfield[5],
        'elevation': airfield[6],
        'launch_type_detection': True if airfield[17] == 1 else False
    }
    AIRFIELD_DATA[(airfield_json['latitude'], airfield_json['longitude'])] = airfield_json

AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
log.debug('Airfields loaded: {}'.format(pprint.pformat(AIRFIELD_LOCATIONS)))
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)

db_conn.close()


def detect_airfield(beacon, flight):
    """
    :param beacon:
    :param type:
    :return:
    """
    detection_radius = float(config['TRACKER']['airfield_detection_radius'])

    # If flight is still near the same airfield, do nothing
    if flight.nearest_airfield and flight.distance_to_nearest_airfield:
        current_distance_to_airfield = measure_distance.distance(
            [float(flight.nearest_airfield['latitude']), float(flight.nearest_airfield['longitude'])],
            (beacon['latitude'], beacon['longitude']))
        if current_distance_to_airfield <= detection_radius:
            flight.distance_to_nearest_airfield = current_distance_to_airfield
            return

    # If not, detect the nearest airfield and update the flight
    _, closest_airfield_index = AIRFIELD_TREE.query((float(beacon['latitude']), float(beacon['longitude'])), 1)
    closest_airfield = AIRFIELD_DATA[AIRFIELD_LOCATIONS[closest_airfield_index]]
    distance_to_nearest = measure_distance.distance(
        [float(closest_airfield['latitude']), float(closest_airfield['longitude'])],
        (beacon['latitude'], beacon['longitude'])).km
    log.debug(("nearest is: {} at {}".format(closest_airfield['name'], distance_to_nearest)))
    flight.nearest_airfield = closest_airfield
    flight.distance_to_nearest_airfield = distance_to_nearest


def detect_tug(tracked_aircraft, flight):
    log.debug('Looking for a tug launch for {}'.format(flight.registration))
    for address in tracked_aircraft:
        if flight.aircraft_type == 2:
            log.info('This IS a tug!')
            return False
        if address == flight.address:
            continue
        other_flight = tracked_aircraft[address]
        if other_flight.takeoff_timestamp and other_flight.takeoff_airfield == flight.takeoff_airfield:
            time_difference = (other_flight.takeoff_timestamp - flight.takeoff_timestamp).total_seconds()
            if -10 < time_difference < 10:
                if other_flight.aircraft_type == 2:
                    log.info("Tug found: {} is towing {} at {}".format(
                        other_flight.address if other_flight.registration == 'UNKNOWN' else other_flight.registration,
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['nice_name']))
                    flight.launch_type = 'aerotow_glider'
                    other_flight.launch_type = 'aerotow_tug'
                else:
                    log.info("Aerotow pair found, can't tell which is the tug though: {} is towing with {} at {}".format(
                        other_flight.address if other_flight.registration == 'UNKNOWN' else other_flight.registration,
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['nice_name']))
                    flight.launch_type = 'aerotow_pair'
                    other_flight.launch_type = 'aerotow_pair'
                aerotow = Aerotow(flight, other_flight)
                flight.tug = other_flight
                flight.aerotow = aerotow
                other_flight.tug = flight
                other_flight.aerotow = aerotow
                return True


def track_aircraft(beacon, save_beacon=True, check_date=True):
    # log.info("track aircraft!")
    # log.info(pprint.pformat(beacon))

    try:
        reference_timestamp = datetime(*time.strptime(beacon['reference_timestamp'], '%Y-%m-%dT%H:%M:%S.%f')[:6])
    except ValueError:
        reference_timestamp = datetime(*time.strptime(beacon['reference_timestamp'], '%Y-%m-%dT%H:%M:%S')[:6])
    beacon['reference_timestamp'] = reference_timestamp

    timestamp = datetime(*time.strptime(beacon['timestamp'], '%Y-%m-%dT%H:%M:%S')[:6])
    beacon['timestamp'] = timestamp

    db_conn = make_database_connection()
    if not db_conn:
        log.error("Unable to connect to database, skipping beacon")
        return

    if save_beacon:
        add_beacon(db_conn.cursor(), beacon)

    try:
        beacon['altitude'] = beacon['altitude'] + BEACON_CORRECTIONS[beacon['receiver_name']]
        log.info('Correction applied for {} beacon. Alt: {}'.format(beacon['receiver_name'], beacon['altitude']))
    except KeyError:
        # log.info('No correction to apply for {} beacon. Alt: {}'.format(beacon['receiver_name'], beacon['altitude']))
        pass

    if beacon['address'] in tracked_aircraft.keys() and check_date:
        # Remove outdated tracking
        if datetime.date(tracked_aircraft[beacon['address']].timestamp) < datetime.today().date():
            tracked_aircraft.pop(beacon['address'])
            log.debug("Removed outdated tracking for: {}".format(beacon['address']))
        else:
            log.debug('Tracking checked and is up to date')

    if beacon['address'] not in tracked_aircraft.keys():
        try:
            device = DEVICE_DICT[beacon['address']]
        except KeyError:
            log.error('Device dict not found for {}'.format(beacon['address']))
            device = None

        if device:
            log.info('Using data in device dict')
            registration = DEVICE_DICT[beacon['address']]['REGISTRATION'].upper() if DEVICE_DICT[beacon['address']]['REGISTRATION'] else 'UNKNOWN'
            aircraft_model = DEVICE_DICT[beacon['address']]['AIRCRAFT_MODEL'] if DEVICE_DICT[beacon['address']]['AIRCRAFT_MODEL'] else None
            competition_number = DEVICE_DICT[beacon['address']]['CN'] if DEVICE_DICT[beacon['address']]['CN'] else None
        else:
            log.info('Setting device data to unknowns')
            registration = 'UNKNOWN'
            aircraft_model = None
            competition_number = None


        log.info('Aircraft {}/{} not tracked yet'.format(registration, beacon['address']))

        new_flight = Flight(
            None,
            beacon['address'],
            beacon['aircraft_type'],
            beacon['altitude'],
            beacon['ground_speed'],
            beacon['receiver_name'],
            # beacon['reference_timestamp'],
            reference_timestamp,
            registration,
            aircraft_model,
            competition_number
        )

        detect_airfield(beacon, new_flight)

        if beacon['ground_speed'] > float(config['TRACKER']['airborne_detection_speed']) and new_flight.agl() > float(config['TRACKER']['airborne_detection_agl']):
            new_flight.status = 'air'
        else:
            new_flight.status = 'ground'
        log.info("Starting to track aircraft {}/{} {}km from {} with status {}".format(registration,
                                                                                       new_flight.address,
                                                                                       new_flight.distance_to_nearest_airfield,
                                                                                       new_flight.nearest_airfield['nice_name'],
                                                                                       new_flight.status))
        log.info("Extra detail for {}/{}: Model: {}, CN: {}".format(registration,
                                                                    new_flight.address,
                                                                    aircraft_model,
                                                                    competition_number))

        tracked_aircraft[beacon['address']] = new_flight
    else:
        log.debug('Updating tracked aircraft')
        flight = tracked_aircraft[beacon['address']]

        # update fields of flight
        detect_airfield(beacon, flight) # updates airfield and distance to airfield
        last_flight_timestamp = flight.timestamp
        flight.update(beacon)

        if flight.status == 'ground' and last_flight_timestamp <= timestamp:

            if beacon['ground_speed'] > float(config['TRACKER']['airborne_detection_speed']) \
            and flight.agl() > float(config['TRACKER']['airborne_detection_agl']):

                # Aircraft launch detected
                # At airfield
                if flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius']):
                    log.info("Adding aircraft {} as launched at {} @ {}".format(
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['name'], flight.timestamp))
                    flight.launch()
                    add_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()
                #2.5 naut. miles
                elif flight.distance_to_nearest_airfield < 4.63:
                    #todo: give airfields a max launch detection range
                    # Not near airfield anymore - tracking for launch has been missed
                    log.info("Adding aircraft {} as launched at {} but we missed it".format(
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['name'],
                        flight.timestamp))
                    # todo: use the time known arg below to srt flag in db
                    flight.launch(time_known=False)
                    #todo: enum/dict the launch types 1: etc.
                    flight.launch_type = 'unknown, nearest field'
                    # prevent launch height tracking
                    flight.launch_height = None
                    flight.launch_complete = True
                    add_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()
                # 2.5 naut. miles
                else:
                    #todo: give airfields a max launch detection range
                    # Not near airfield at all
                    log.info("Adding aircraft {} as launched near(ish) {} but outside 2.5 nautical mile radius".format(
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['name'],
                        flight.timestamp))
                    flight.launch(time_known=False)
                    # todo: use the time known arg below to srt flag in db
                    #todo: enum/dict the launch types 1:winch etc.
                    flight.launch_type = 'unknown, {}km'.format(round(flight.distance_to_nearest_airfield, 2))
                    # prevent launch height tracking
                    flight.takeoff_airfield = 'UNKNOWN'
                    flight.launch_height = None
                    flight.launch_complete = True
                    add_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()

        elif flight.status == 'air':
            # log.info('Speed: {}, {} | AGL: {}, {} | Dist: {} {} | Climb: {} {}'.format(
            #     beacon['ground_speed'], beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed']),
            #     flight.agl(), flight.agl() < float(config['TRACKER']['landing_detection_agl']),
            #     flight.distance_to_nearest_airfield, flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius']),
            #     beacon['climb_rate'], beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate'])))

                # todo remove unused flight object fields eg 'tracking_launch_height'

            if flight.takeoff_timestamp and not flight.launch_complete:

                time_since_launch = flight.seconds_since_launch()
                log.debug("time since launch: {}".format(time_since_launch))

                # todo config

                launch_tracking_times= {
                    'winch': 60,
                    'max': 1000
                }

                if time_since_launch <= launch_tracking_times['max']:
                    # log.info("Updating aircraft {} launch height".format(flight.registration))
                    # log.info("{} launch height is: {}".format(flight.registration, flight.launch_height))
                    # log.info("{} launch vertical speed is {}".format(flight.registration, beacon['climb_rate']))
                    # log.info("{} launch type is {}".format(flight.registration, flight.launch_type))

                    if beacon['climb_rate'] > flight.max_launch_climb_rate:
                        flight.max_launch_climb_rate = beacon['climb_rate']

                    if not flight.launch_type:
                        # detect tug will update the launch type if a flarm tug is detected
                        if not detect_tug(tracked_aircraft, flight):
                            if len(flight.launch_beacon_heights) >= 5:
                                log.info('Deciding launch type for {} at {} @{} based on gradient: {}'.format(
                                    flight.registration,
                                    flight.nearest_airfield['nice_name'],
                                    flight.takeoff_timestamp,
                                    flight.launch_gradient()
                                ))
                                if flight.launch_gradient() > float(config['TRACKER']['winch_detection_gradient']):
                                    flight.set_launch_type('winch')
                                elif len(flight.launch_beacon_heights) >= 10:
                                    try:
                                        flight.average_launch_climb_rate = mean(flight.launch_climb_rates.values())
                                    except StatisticsError:
                                        log.info("No data to average, skipping")



                                    # log.info('Deciding launch type for {} at {} @{} based on climb rates: {}'.format(
                                    #     flight.registration,
                                    #     flight.takeoff_airfield,
                                    #     flight.takeoff_timestamp,
                                    #     pprint.pformat(flight.launch_climb_rates)
                                    # ))
                                    flight.set_launch_type('aerotow_sl')
                elif not flight.launch_complete:
                    flight.launch_complete = True
                    log.info(
                        '{} launch complete (timeout) at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}'.format(
                            flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                            flight.nearest_airfield['nice_name'],
                            flight.launch_type,
                            flight.launch_height * 3.281,
                            time_since_launch,
                            flight.average_launch_climb_rate
                        ))
                    update_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()

                if flight.launch_type == 'winch' and time_since_launch > launch_tracking_times['winch']:
                    flight.launch_complete = True
                    log.info(
                        '{} launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}'.format(
                            flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                            flight.nearest_airfield['nice_name'],
                            flight.launch_type,
                            flight.launch_height * 3.281,
                            time_since_launch,
                            flight.average_launch_climb_rate,
                        ))
                    log.info('Launch gradients: {}'.format(flight.launch_gradients))
                    update_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()

                if flight.launch_type in ['aerotow_glider', 'aerotow_pair', 'aerotow_tug']:
                    try:
                        flight.update_aerotow(beacon)
                        update_flight(db_conn.cursor(), flight.to_dict())
                        db_conn.commit()
                        update_flight(db_conn.cursor(), flight.tug.to_dict())
                        db_conn.commit()
                    except AttributeError as err:
                            log.error(err)
                            log.error(
                                'Something went wrong with aerotow update for {}/{}, aborting'.format(flight.registration,
                                                                                               flight.address))
                            flight.aerotow.abort()

                if flight.launch_type in ['aerotow_sl', 'tug']:
                    try:
                        recent_average = mean(list(flight.launch_climb_rates.values())[-10:])
                        recent_average_diff = recent_average - flight.average_launch_climb_rate

                        if recent_average_diff < -2 or recent_average_diff > 2:
                            sl = None
                            if recent_average_diff < -2:
                                sl = "sink"
                            if recent_average_diff > 2:
                                sl = "lift"
                            flight.launch_complete = True
                            log.info('Launch gradients: {}'.format(flight.launch_gradients))
                            # log.info(flight.launch_climb_rates.values())
                            log.info(
                                '{} launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}, Recent Average Vertical: {}, Difference: {}, Sink/lift: {}'.format(
                                    flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                                    flight.nearest_airfield['nice_name'],
                                    flight.launch_type,
                                    flight.launch_height * 3.281,
                                    time_since_launch,
                                    flight.average_launch_climb_rate,
                                    recent_average,
                                    recent_average_diff,
                                    sl
                                ))
                            update_flight(db_conn.cursor(), flight.to_dict())
                            db_conn.commit()
                    except StatisticsError:
                        log.info("No data to average, skipping")

            elif flight.status == 'air'\
                    and beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed'])\
                    and flight.agl() < float(config['TRACKER']['landing_detection_agl'])\
                    and flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius'])\
                    and beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate']):

                log.info("Aircraft {} detected below airborne detection criteria".format(
                    flight.address if flight.registration == 'UNKNOWN' else flight.registration))

                if last_flight_timestamp <= timestamp:

                    # Aircraft landing detected
                    # todo: landout detection
                    flight.status = 'ground'
                    flight.landing_timestamp = timestamp
                    flight.landing_airfield = flight.nearest_airfield['id']

                    if flight.takeoff_timestamp and not flight.launch_complete:
                        flight.launch_type = 'winch l/f'

                    log.info("Updating aircraft {} as landed at {}".format(
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.nearest_airfield['name']))

                    log.info('Landing data... ground_speed: {}, agl: {}, climb_rate: {}'.format(beacon['ground_speed'], flight.agl(), beacon['climb_rate']))

                    if flight.takeoff_timestamp:
                        update_flight(db_conn.cursor(), flight.to_dict())
                        db_conn.commit()
                    else:
                        add_flight(db_conn.cursor(), flight.to_dict())
                        db_conn.commit()
                    log.info('Aircraft {} flew from {} to {}'.format(
                        flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                        flight.takeoff_timestamp,
                        flight.landing_timestamp))
                    if flight.takeoff_timestamp and flight.landing_timestamp:
                        draw_alt_graph(
                            db_conn.cursor(),
                            flight
                        )
                    tracked_aircraft.pop(flight.address)
                # else:
                #     log.info("NOT Updating aircraft {} as landed at {}".format(
                #         flight.address if flight.registration == 'UNKNOWN' else flight.registration,
                #         flight.landing_airfield))
                #     log.info('NOT Landing data... ground_speed: {}, agl: {}, climb_rate: {}'.format(beacon['ground_speed'],
                #                                                                                 flight.agl(),
                #                                                                                 beacon['climb_rate']))

    # log.info('Tracked aircraft =========================')
    # for flight in tracked_aircraft:
    #     log.info(pprint.pformat(tracked_aircraft[flight].to_dict()))
    # log.info('End Tracked aircraft {} {}'.format(len(tracked_aircraft), '======================'))
    db_conn.close()

import time

beacon_count = 0

def process_beacon(ch, method, properties, body):
    # log.info('Beacon process start')
    # global  beacon_count
    # start = time.time()
    try:
        beacon = json.loads(body)
        try:
            if beacon['beacon_type'] in ['aprs_aircraft', 'flarm']:
                log.debug('Aircraft beacon received')
                if beacon['aircraft_type'] in [1, 2]:
                    try:
                        track_aircraft(beacon)
                    except TypeError as e:
                        log.info('Type error while tracking: {}'.format(e))
                        raise
                else:
                    log.debug("Not a glider or tug")
        except KeyError as e:
            log.debug('Beacon type field not found: {}'.format(e))
    except ParseError as e:
        log.error('Parse error: {}'.format(e))
    end = time.time()
    # beacon_count += 1
    # log.info('Beacon took {} to process'.format(end - start))
    # log.info('Beacon count: {}'.format(beacon_count))



log.info("Checking database for active flights")
db_conn = make_database_connection()
if db_conn:
    database_flights = get_currently_airborne_flights(db_conn.cursor(dictionary=True))
    db_conn.close()
else:
    log.error('Unable to retrieve database flights')
    database_flights = {}

for db_flight in database_flights:
    db_tracked_flight = Flight(db_flight['airfield'],
                               db_flight['address'],
                               db_flight['aircraft_type'],
                               db_flight['altitude'],
                               db_flight['ground_speed'],
                               db_flight['receiver_name'],
                               db_flight['reference_timestamp'],
                               db_flight['registration'],
                               db_flight['aircraft_model'],
                               db_flight['competition_number'])
    db_tracked_flight.takeoff_timestamp = db_flight['takeoff_timestamp']
    db_tracked_flight.landing_timestamp = db_flight['landing_timestamp']
    db_tracked_flight.status = db_flight['status']
    db_tracked_flight.tracking_launch_height = db_flight['tracking_launch_height']
    db_tracked_flight.tracking_launch_start_time = db_flight['tracking_launch_start_time']
    db_tracked_flight.launch_height = db_flight['launch_height']
    db_tracked_flight.takeoff_airfield = db_flight['takeoff_airfield']
    db_tracked_flight.landing_airfield = db_flight['landing_airfield']
    db_tracked_flight.launch_type = db_flight['launch_type']
    db_tracked_flight.average_launch_climb_rate = db_flight['average_launch_climb_rate']
    db_tracked_flight.max_launch_climb_rate = db_flight['max_launch_climb_rate']
    db_tracked_flight.launch_complete = True if db_flight['launch_complete'] == 1 else False
    # todo: other flight as object
    db_tracked_flight.tug = db_flight['tug_registration']

    tracked_aircraft[db_tracked_flight.address] = db_tracked_flight

log.info("Database flights =========")
for aircraft in tracked_aircraft:
    log.info(pprint.pformat(tracked_aircraft[aircraft].to_dict()))
log.info("=========")

# LIVE get beacons

# def connect_to_ogn_and_run(filter_string):
#     if len(filter_string.split(' ')) > 9:
#         log.error("Too many aprs filters")
#     else:
#         log.info('Connecting to OGN gateway')
#         client = AprsClient(aprs_user='N0CALL', aprs_filter=aprs_filter)
#         client.connect()
#         try:
#             client.run(callback=process_beacon, autoreconnect=True)
#         except KeyboardInterrupt:
#             client.disconnect()
#             raise
#         except AttributeError as err:
#             log.error(err)


def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host']))
    channel = connection.channel()

    channel.basic_consume(queue='received_beacons',
                      auto_ack=True,
                      on_message_callback=process_beacon)

    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
