import configparser
import requests
import json
import logging
import os

import pprint

import mysql.connector

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between, get_raw_beacons_between, get_airfields, get_filters_by_country_codes, get_active_airfields_for_countries

from charts import draw_alt_graph

from datetime import datetime

from geopy import distance as measure_distance

from scipy.spatial import kdtree

from flight import Flight

from statistics import mean, StatisticsError

config = configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

tracked_aircraft = {}


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


db_conn = make_database_connection()

AIRFIELD_DATA = {}
for airfield in get_active_airfields_for_countries(db_conn.cursor(), config['TRACKER']['track_countries'].split(',')):
    airfield_json = {
        'id': airfield[0],
        'name': airfield[1],
        'nice_name': airfield[2],
        'latitude': airfield[3],
        'longitude': airfield[4],
        'elevation': airfield[5]
    }
    AIRFIELD_DATA[(airfield_json['latitude'], airfield_json['longitude'])] = airfield_json

AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
log.debug('Airfields loaded: {}'.format(pprint.pformat(AIRFIELD_LOCATIONS)))
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)

db_conn.close()


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
                    log.info("Tug found: {} is towing {} at {}".format(other_flight.registration, flight.registration, flight.takeoff_airfield))
                    flight.launch_type = 'aerotow_glider'
                else:
                    log.info("Aerotow pair found, can't tell which is the tug though: {} is towing with {} at {}".format(other_flight.registration, flight.registration, flight.takeoff_airfield))
                    flight.launch_type = 'aerotow_pair'
                    other_flight.launch_type = 'aerotow_pair'
                flight.tug = other_flight.registration
                other_flight.tug = flight.registration
                return True


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

    if beacon['address'] in tracked_aircraft.keys():
        # Remove outdated tracking
        if datetime.date(tracked_aircraft[beacon['address']].timestamp) < datetime.today().date():
            tracked_aircraft.pop(beacon['address'])
            log.debug("Removed outdated tracking for: {}".format(beacon['address']))
        else:
            log.debug('Tracking checked and is up to date')

    if beacon['address'] not in tracked_aircraft.keys():
        log.debug('Aircraft {} not tracked yet'.format(beacon['address']))
        new_flight = Flight(
            None,
            beacon['address'],
            beacon['aircraft_type'],
            beacon['altitude'],
            beacon['ground_speed'],
            beacon['receiver_name'],
            beacon['reference_timestamp'],
            registration
        )
        detect_airfield(beacon, new_flight)

        if beacon['ground_speed'] > 20 and beacon['altitude'] - new_flight.nearest_airfield['elevation'] > 200:
            new_flight.status = 'air'
        else:
            new_flight.status = 'ground'
        log.debug("Starting to track aircraft ".format(registration))
        tracked_aircraft[beacon['address']] = new_flight
    else:
        log.debug('Updating tracked aircraft')
        flight = tracked_aircraft[beacon['address']]

        # update fields of flight
        detect_airfield(beacon, flight) # updates airfield and distance to airfield
        flight.update(beacon)

        if beacon['ground_speed'] >= 30 and flight.agl() > 15:
            log.debug("airborne aircraft detected")

            if flight.status == 'ground':
                # Aircraft launch detected
                # At airfield
                if flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius']):
                    log.info("Adding aircraft {} as launched at {} @{}".format(flight.registration, flight.nearest_airfield['name'], flight.timestamp))
                    flight.launch()
                else:
                    # Not near airfield anymore - tracking for launch has been missed
                    log.info("Adding aircraft {} as launched near {} but we missed it".format(flight.registration, flight.nearest_airfield['name'], flight.timestamp))
                    flight.launch(time_known=False)
                    #todo: enum/dict the launch types 1:winch etc.
                    flight.launch_type = 'unknown, nearest field'
                    # prevent launch height tracking
                    flight.launch_complete = True
                add_flight(db_conn.cursor(), flight.to_dict())
                db_conn.commit()

            else:

                # todo remove unsued flight object fields eg 'tracking_launch_height'

                if flight.takeoff_timestamp and not flight.launch_complete:

                    time_since_launch = flight.seconds_since_launch()
                    log.debug("time since launch: {}".format(time_since_launch))

                    # todo config

                    max_tracking_time = 1000

                    if time_since_launch <= max_tracking_time:
                        log.debug("Updating aircraft {} launch height".format(flight.registration))
                        log.debug("{} launch height is: {}".format(flight.registration, flight.launch_height))
                        log.debug("{} launch vertical speed is {}".format(flight.registration, beacon['climb_rate']))
                        log.debug("{} launch type is {}".format(flight.registration, flight.launch_type))

                        if beacon['climb_rate'] > flight.max_launch_climb_rate:
                            flight.max_launch_climb_rate = beacon['climb_rate']

                        if flight.agl() > 100:
                            flight.add_launch_climb_rate_point(beacon['climb_rate'])
                            flight.average_launch_climb_rate = mean(flight.launch_climb_rates)

                            if not flight.launch_type:
                                if not detect_tug(tracked_aircraft, flight):
                                    if len(flight.launch_climb_rates) > 10:
                                        if flight.max_launch_climb_rate > 7:
                                            flight.set_launch_type('winch')
                                        else:
                                            flight.set_launch_type('aerotow_sl')
                            try:
                                recent_average = mean(flight.launch_climb_rates[-15:])
                                recent_average_diff = recent_average - flight.average_launch_climb_rate

                                if recent_average_diff < -1.5 or recent_average_diff > 1.5:
                                    sl = None
                                    if recent_average_diff < -1.5:
                                        sl = "sink"
                                    if recent_average_diff > 1.5:
                                        sl ="lift"
                                    flight.launch_complete = True
                                    log.info(flight.launch_climb_rates)
                                    log.info('{} launch complete at {}! Launch type: {}, Launch height: {}, Launch time: {}, Average vertical: {}, Recent Average Vertical: {}, Difference: {}, Sink/lift: {}'.format(
                                        flight.registration,
                                        flight.takeoff_airfield,
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

        elif beacon['ground_speed'] <= 30 and beacon['altitude'] - flight.nearest_airfield['elevation'] <= 15:
            log.debug("aircraft detected on ground")

            if flight.status == 'air' and flight.distance_to_nearest_airfield < float(config['TRACKER']['airfield_detection_radius']):
                # Aircraft landing detected
                flight.status = 'ground'
                flight.landing_timestamp = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S"))
                flight.landing_airfield = flight.nearest_airfield['name']

                if flight.takeoff_timestamp and not flight.launch_complete:
                    flight.launch_type = 'winch l/f'

                log.info("Updating aircraft {} as landed".format(registration))

                if flight.takeoff_timestamp:
                    update_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()
                else:
                    add_flight(db_conn.cursor(), flight.to_dict())
                    db_conn.commit()
                log.info('Aircraft {} flew from {} to {}'.format(flight.registration, flight.takeoff_timestamp, flight.landing_timestamp))
                if flight.takeoff_timestamp and flight.landing_timestamp:
                    draw_alt_graph(
                        db_conn.cursor(),
                        flight,
                        config['TRACKER']['chart_directory']
                    )
                tracked_aircraft.pop(flight.address)

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
                if beacon['aircraft_type'] in [1, 2]:
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

for db_flight in database_flights:
    db_tracked_flight = Flight(db_flight[1], db_flight[2], db_flight[3], db_flight[4], db_flight[5], db_flight[6], db_flight[7], db_flight[8])
    db_tracked_flight.takeoff_timestamp = db_flight[9]
    db_tracked_flight.landing_timestamp = db_flight[10]
    db_tracked_flight.status = db_flight[11]
    db_tracked_flight.tracking_launch_height = db_flight[13]
    db_tracked_flight.tracking_launch_start_time = db_flight[14]
    db_tracked_flight.launch_height = db_flight[12]
    db_tracked_flight.takeoff_airfield = db_flight[15]
    db_tracked_flight.landing_airfield = db_flight[16]

    tracked_aircraft[db_tracked_flight.address] = db_tracked_flight
    pprint.pprint(db_tracked_flight.to_dict())

log.info("=========")
for aircraft in tracked_aircraft:
    log.info(pprint.pformat(tracked_aircraft[aircraft].to_dict()))
log.info("=========")

# LIVE get beacons

track_countries = config['TRACKER']['track_countries'].split(',')
db_conn = make_database_connection()
filters = get_filters_by_country_codes(db_conn.cursor(), track_countries)
db_conn.close()
aprs_filter = ' '.join(filters)

client = AprsClient(aprs_user='N0CALL', aprs_filter=aprs_filter)

client.connect()
try:
    client.run(callback=process_beacon, autoreconnect=True)
except KeyboardInterrupt:
    print('\nStop ogn gateway')
    client.disconnect()


# Debug Get beacons from DB

# need to also prevent checking data is up to date
# comment out the live import above

# db_conn = make_database_connection()
# # beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-20 10:00:00', '2020-12-20 18:00:00')
# # beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-31 10:00:00', '2020-12-31 18:00:00')
# beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-27 10:00:00', '2020-12-27 18:00:00')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD51CC', '2020-12-22 15:27:19', '2020-12-22 15:33:15')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD5133', '2020-12-22 15:44:33', '2020-12-22 16:08:56')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), '405612', '2020-12-22 15:35:59', '2020-12-22 15:52:17')
#
#
# print(len(beacons))
#
# for beacon in beacons:
#     # log.warning(beacon)
#     if beacon['aircraft_type'] in [1,2]:
#         beacon['timestamp'] = beacon['timestamp'].replace(year=2021, day=9, month=1)
#         beacon['reference_timestamp'] = beacon['reference_timestamp'].replace(year=2021, day=9, month=1)
#         track_aircraft(beacon, save_beacon=False)
