import configparser
import requests
import json
import logging
import os

import pprint

import mysql.connector

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between, get_raw_beacons_between

from charts import draw_alt_graph

from datetime import datetime

from geopy import distance as measure_distance

from scipy.spatial import kdtree

from aircraft import Aircraft

config = configparser.ConfigParser()
config.read('config.ini')

tracked_airfield_name = config['TRACKER']['tracked_airfield']
tracked_airfield = json.loads(config['AIRFIELDS'][tracked_airfield_name])

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

tracked_aircraft = {}

#debug
# counted_launches = 0
# average_launch_speed = 0

#
# AIRCRAFT_DATA_TEMPLATE = {
#     'airfield': None,
#     'address': None,
#     'address_type': None,
#     'altitude': None,
#     'ground_speed': None,
#     'receiver_name': None,
#     'reference_timestamp': None,
#     'registration': None,
#     'takeoff_timestamp': None,
#     'takeoff_airfield': None,
#     'landing_timestamp': None,
#     'landing_airfield': None,
#     'status': None,
#     'launch_type': None,
#     'max_launch_climb_rate': 0,
#     'launch_climb_rates': []
# }

AIRFIELD_DATA = {}
for airfield in config['AIRFIELDS']:
    airfield_json = json.loads(config['AIRFIELDS'][airfield])
    AIRFIELD_DATA[(float(airfield_json['latitude']), float(airfield_json['longitude']))] = airfield_json

AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)


def make_database_connection(retry_counter=0):
    if retry_counter > 5:
        log.error("Failed to connect to database after 5 retries")
        return False
    try:
        conn = mysql.connector.connect(
            user=config['TRACKER']['database_user'],
            password=config['TRACKER']['database_password'],
            host=config['TRACKER']['database_host'],
            database=config['TRACKER']['database'])
        return conn
    except mysql.connector.errors.InterfaceError as err:
        log.error(err)
        retry_counter += 1
        return make_database_connection(retry_counter)

def import_device_data():
    device_data = requests.get(config['TRACKER']['device_data_url']).text

    device_dict = {}

    for line in device_data.splitlines():
        if line[0] == '#':
            continue
        else:
            split_line = line.split(',')
            device_dict[split_line[1].strip("'")] = split_line[3].strip("'")

    with open('ogn-ddb.json', 'w') as ddb_data:
        ddb_data.write(json.dumps(device_dict))

    return device_dict


def detect_airfield(beacon):
    """
    :param beacon:
    :param type:
    :return:
    """
    # todo: We need a database table for airfields rather than config
    detection_radius = float(config['TRACKER']['airfield_detection_radius'])

    _, closest_airfield_index = AIRFIELD_TREE.query((float(beacon['latitude']), float(beacon['longitude'])), 1)
    closest_airfield = AIRFIELD_DATA[AIRFIELD_LOCATIONS[closest_airfield_index]]
    distance_to_nearest = measure_distance.distance(
        [float(closest_airfield['latitude']), float(closest_airfield['longitude'])],
        (beacon['latitude'], beacon['longitude'])).km
    log.debug(("nearest is: {} at {}".format(closest_airfield['name'], distance_to_nearest)))

    if distance_to_nearest < detection_radius:
        return closest_airfield, True
    else:
        return closest_airfield, False


def get_airfield(airfield_name):
    return json.loads(config['AIRFIELDS'][airfield_name])


def track_aircraft(beacon, save_beacon=True):

    log.debug("track aircraft!")

    db_conn = make_database_connection()
    if not db_conn:
        log.error("Unable to connect to database, skipping beacon")
        return

    if save_beacon:
        add_beacon(db_conn.cursor(), beacon)

    try:
        with open('ogn-ddb.json') as ogn_ddb:
            device_dict = json.load(ogn_ddb)
    except IOError:
        device_dict = import_device_data()

    try:
        registration = device_dict[beacon['address']].upper()
    except KeyError:
        registration = 'UNKNOWN'

    # if beacon['address'] in tracked_aircraft.keys():
    #     # Remove outdated tracking
    #     if datetime.date(tracked_aircraft[beacon['address']]['reference_timestamp']) < datetime.today().date():
    #         tracked_aircraft.pop(beacon['address'])
    #         log.debug("Removed outdated tracking for: {}".format(beacon['address']))
    #     else:
    #         log.debug('Tracking checked and is up to date')

    airfield, at_airfield = detect_airfield(beacon)
    # todo: correct debug
    airfield_name = airfield['name'].lower()
    if beacon['address'] not in tracked_aircraft.keys():
        log.debug('Aircraft {} not tracked yet'.format(beacon['address']))
        new_aircraft = Aircraft(airfield_name,
                                beacon['address'],
                                beacon['address_type'],
                                beacon['altitude'],
                                beacon['ground_speed'],
                                beacon['receiver_name'],
                                beacon['reference_timestamp'],
                                registration)

        # new_aircraft['airfield'] = airfield_name
        # new_aircraft['address'] = beacon['address']
        # new_aircraft['address_type'] = beacon['address_type']
        # new_aircraft['altitude'] = beacon['altitude']
        # new_aircraft['ground_speed'] = beacon['ground_speed']
        # new_aircraft['receiver_name'] = beacon['receiver_name']
        # new_aircraft['reference_timestamp'] = beacon['reference_timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
        # new_aircraft['registration'] = registration + '_TEST'


        if beacon['ground_speed'] > 20 and beacon['altitude'] - airfield['elevation'] > 200:
            new_aircraft.status = 'air'
        else:
            new_aircraft.status = 'ground'
        log.debug("Starting to track aircraft ".format(registration))
        tracked_aircraft[beacon['address']] = new_aircraft
    else:
        log.debug('Updating tracked aircraft')
        aircraft = tracked_aircraft[beacon['address']]
        aircraft.airfield = airfield_name

        if beacon['ground_speed'] >= 30 and beacon['altitude'] - airfield['elevation'] > 15:
            log.debug("airborne aircraft detected")

            if aircraft.status == 'ground' and at_airfield:

                #debug
                # global counted_launches
                # counted_launches += 1

                # Aircraft launch detected
                logging.info('Before launch' + '='*10)
                logging.info(pprint.pformat(aircraft.to_dict()))
                logging.info('Before launch' + '='*10)
                aircraft.status = 'air'
                aircraft.takeoff_timestamp = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
                aircraft.takeoff_airfield = airfield_name
                aircraft.launch_height = beacon['altitude'] - airfield['elevation']
                logging.info('After launch' + '='*10)
                logging.info(pprint.pformat(aircraft.to_dict()))
                logging.info('After launch' + '='*10)
                log.info("Adding aircraft {} as launched at {}".format(registration, airfield_name))
                add_flight(db_conn.cursor(), aircraft.to_dict())
            else:
                # todo detailed launch height calculation
                # - detect aero/winch
                # todo remove unsued aircraft object fields eg 'tracking_launch_height'

                # {'address': 'DDE6A5',
                #  'address_type': 2,
                #  'aircraft_type': 1,
                #  'altitude': 276.1488,
                #  'aprs_type': 'position',
                #  'beacon_type': 'flarm',
                #  'climb_rate': 15.79372,
                #  'comment': 'id06DDE6A5 +3109fpm -0.2rot 15.5dB +2.1kHz gps1x1',
                #  'dstcall': 'OGFLR',
                #  'error_count': None,
                #  'frequency_offset': 2.1,
                #  'gps_quality': {'horizontal': 1, 'vertical': 1},
                #  'ground_speed': 51.85110519115846,
                #  'hardware_version': None,
                #  'latitude': 53.021166666666666,
                #  'longitude': -0.9168000000000001,
                #  'name': 'FLRDDE6A5',
                #  'raw_message': "FLRDDE6A5>OGFLR,qAS,EGBN:/114734h5301.27N/00055.00W'067/028/A=000906 "
                #                 '!W08! id06DDE6A5 +3109fpm -0.2rot 15.5dB +2.1kHz gps1x1',
                #  'real_address': None,
                #  'receiver_name': 'EGBN',
                #  'reference_timestamp': datetime.datetime(2021, 1, 4, 11, 47, 38, 963901),
                #  'relay': None,
                #  'signal_power': None,
                #  'signal_quality': 15.5,
                #  'software_version': None,
                #  'stealth': False,
                #  'symbolcode': "'",
                #  'symboltable': '/',
                #  'timestamp': datetime.datetime(2021, 1, 4, 11, 47, 34),
                #  'track': 67,
                #  'turn_rate': -0.6000000000000001}
                if aircraft.takeoff_timestamp and not aircraft.launch_complete:
                    time_since_launch = (beacon['timestamp'] - aircraft.takeoff_timestamp).total_seconds()
                    log.debug("time since launch: {}".format(time_since_launch))

                    # todo config

                    winch_tracking_time = 100
                    aerotow_self_tracking_time = 900

                    if aircraft.launch_type == 'aerotow':
                        launch_tracking_time = aerotow_self_tracking_time
                    else:
                        # Assume winch until proven otherwise
                        launch_tracking_time = winch_tracking_time

                    if time_since_launch <= launch_tracking_time:
                        #debug
                        # global average_launch_speed
                        # average_launch_speed = average_launch_speed +

                        from statistics import mean, StatisticsError

                        log.debug("Updating aircraft {} launch height".format(aircraft.registration))
                        log.debug("{} launch height is: {}".format(aircraft.registration, aircraft.launch_height))
                        log.debug("{} launch vertical speed is {}".format(aircraft.registration, beacon['climb_rate']))
                        log.debug("{} launch type is {}".format(aircraft.registration, aircraft.launch_type))

                        if beacon['climb_rate'] > aircraft.max_launch_climb_rate:
                            aircraft.max_launch_climb_rate = beacon['climb_rate']

                        if time_since_launch > 5:
                            if aircraft.average_launch_climb_rate > 5:
                                aircraft.launch_type = 'winch'
                            else:
                                aircraft.launch_type = 'aerotow'

                            if len(aircraft.launch_climb_rates) > 10:

                                try:

                                    recent_average = mean(aircraft.launch_climb_rates[-15:])


                                    recent_average_diff = recent_average - aircraft.average_launch_climb_rate


                                    if recent_average_diff < -1.5 or recent_average_diff > 1.5:
                                        sl = None
                                        if recent_average_diff < -1.5:
                                            sl = "sink"
                                        if recent_average_diff > 1.5:
                                            sl ="lift"
                                        aircraft.launch_complete = True
                                        log.info(pprint.pformat(aircraft.launch_climb_rates))
                                        log.info('{} launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}, Recent Average Vertical: {}, Difference: {}, Sink/lift: {}'.format(
                                            aircraft.registration,
                                            aircraft.takeoff_airfield,
                                            aircraft.launch_type,
                                            aircraft.launch_height * 3.281,
                                            time_since_launch,
                                            aircraft.average_launch_climb_rate,
                                            recent_average,
                                            recent_average_diff,
                                            sl
                                        ))
                                except StatisticsError:
                                    log.info("No data to average, skipping")


                            aircraft.add_launch_climb_rate_point(beacon['climb_rate'])
                            aircraft.average_launch_climb_rate = mean(aircraft.launch_climb_rates)

                        try:
                            # Record the maximum launch height
                            if beacon['altitude'] - airfield['elevation'] > aircraft.launch_height:
                                aircraft.launch_height = beacon['altitude'] - airfield['elevation']
                                update_flight(db_conn.cursor(), aircraft.to_dict())
                                db_conn.commit()
                        except TypeError:
                            # Probably a tracker restart error, just set the launch height as current AGL
                            aircraft.launch_height = beacon['altitude'] - airfield['elevation']
                            update_flight(db_conn.cursor(), aircraft.to_dict())
                            db_conn.commit()

        elif beacon['ground_speed'] <= 30 and beacon['altitude'] - airfield['elevation'] <= 15:
            log.debug("aircraft detected on ground")

            if aircraft.status == 'air' and at_airfield:
                # Aircraft landing detected
                aircraft.status = 'ground'
                aircraft.landing_timestamp = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S"))
                aircraft.landing_airfield = airfield_name
                log.info("Updating aircraft {} as landed".format(registration))

                if aircraft.takeoff_timestamp:
                    update_flight(db_conn.cursor(), aircraft.to_dict())
                    db_conn.commit()
                else:
                    add_flight(db_conn.cursor(), aircraft.to_dict())
                    db_conn.commit()
                log.info('Aircraft {} flew from {} to {}'.format(aircraft.registration, aircraft.takeoff_timestamp, aircraft.landing_timestamp))
                if aircraft.takeoff_timestamp and aircraft.landing_timestamp:
                    draw_alt_graph(
                        db_conn.cursor(),
                        aircraft,
                        config['TRACKER']['chart_directory']
                    )
                tracked_aircraft.pop(aircraft.address)

    log.debug('Tracked aircraft =========================')
    for flight in tracked_aircraft:
        log.debug(pprint.pformat(tracked_aircraft[flight].to_dict()))
    log.debug('End Tracked aircraft {} {}'.format(len(tracked_aircraft), '======================'))
    db_conn.close()


def process_beacon(raw_message):
    try:
        beacon = parse(raw_message)
        try:
            if beacon['beacon_type'] in ['aprs_aircraft', 'flarm']:
                log.debug('Aircraft beacon received')
                if beacon['aircraft_type'] in [1,2]:
                    track_aircraft(beacon)
                else:
                    log.debug("Not a glider or tug")
        except KeyError as e:
            log.debug('Beacon type field not found')
            log.debug(e)
            pass
    except ParseError as e:
        log.error('Error, {}'.format(e.message))


log.info('Importing device data')
import_device_data()

log.info("Checking database for active flights")
db_conn = make_database_connection()
if db_conn:
    database_flights = get_currently_airborne_flights(db_conn.cursor())
    db_conn.close()
else:
    log.error('Unable to retrieve database flights')
    database_flights = {}



for flight in database_flights:
    db_flight = Aircraft(flight[1], flight[2], flight[3], flight[4], flight[5], flight[6], flight[7], flight[8])
    db_flight.takeoff_timestamp = flight[9]
    db_flight.landing_timestamp = flight[10]
    db_flight.status = flight[11]
    db_flight.tracking_launch_height = flight[13]
    db_flight.tracking_launch_start_time = flight[14]
    db_flight.launch_height = flight[12]
    db_flight.takeoff_airfield = flight[15]
    db_flight.landing_airfield = flight[16]

    tracked_aircraft[db_flight.address] = db_flight
    pprint.pprint(db_flight.to_dict())

log.info("=========")
for aircraft in tracked_aircraft:
    log.info(pprint.pformat(tracked_aircraft[aircraft].to_dict()))
log.info("=========")


# client = AprsClient(aprs_user='N0CALL', aprs_filter="r/{latitude}/{longitude}/{tracking_radius}".format(tracking_radius=config['TRACKER']['tracking_radius'], **tracked_airfield))
# client.connect()
# try:
#     client.run(callback=process_beacon, autoreconnect=True)
# except KeyboardInterrupt:
#     print('\nStop ogn gateway')
#     client.disconnect()

from flight_tracker_squirreler import get_raw_beacons_for_address_between

db_conn = make_database_connection()
beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-24 07:00:00', '2020-12-24 18:00:00')
# beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD51CC', '2020-12-22 15:27:19', '2020-12-22 15:33:15')
# beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD5133', '2020-12-22 15:44:33', '2020-12-22 16:08:56')
# beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), '405612', '2020-12-22 15:35:59', '2020-12-22 15:52:17')


print(len(beacons))

for beacon in beacons:
    # log.warning(beacon)
    beacon['address'] = beacon['address']
    track_aircraft(beacon, save_beacon=False)
