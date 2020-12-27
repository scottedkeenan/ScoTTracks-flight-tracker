import configparser
import requests
import json
from math import radians, cos, sin, asin, sqrt
import logging
import os

import pprint

import mysql.connector

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between

from charts import draw_alt_graph

from datetime import datetime, timezone, timedelta

from geopy import distance as measure_distance

config = configparser.ConfigParser()
config.read('config.ini')

tracked_airfield_name = config['TRACKER']['tracked_airfield']
tracked_airfield = json.loads(config['AIRFIELDS'][tracked_airfield_name])

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

AIRCRAFT_DATA_TEMPLATE = {
    'airfield': None,
    'address': None,
    'address_type': None,
    'altitude': None,
    'ground_speed': None,
    'receiver_name': None,
    'reference_timestamp': None,
    'registration': None,
    'takeoff_timestamp': None,
    'takeoff_airfield': None,
    'landing_timestamp': None,
    'landing_airfield': None,
    'status': None,
}


def make_database_connection():
    conn = mysql.connector.connect(
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        host=config['TRACKER']['database_host'],
        database = config['TRACKER']['database'])
    return conn


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
    nearest = 'unknown'
    nearest_distance = None
    for airfield in config['AIRFIELDS']:
        airfield_data = json.loads(config['AIRFIELDS'][airfield])

        distance = measure_distance.distance(
            (airfield_data['latitude'], airfield_data['longitude']),
            (beacon['latitude'], beacon['longitude'])).km

        log.debug("Distance to: {} is {}".format(airfield_data['name'], distance))

        if distance < detection_radius:
            # return airfield, airfield_data['name'].lower().replace(' -', '_'), True
            return airfield_data, True
        elif nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest = airfield_data
    log.debug("nearest is: {} at {}".format(nearest, nearest_distance))
    return nearest, False


def get_airfield(airfield_name):
    return json.loads(config['AIRFIELDS'][airfield_name])


def track_aircraft(beacon):
    log.debug("track aircraft!")

    db_conn = make_database_connection()

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
        if datetime.date(tracked_aircraft[beacon['address']]['reference_timestamp']) < datetime.today().date():
            tracked_aircraft.pop(beacon['address'])
            log.debug("Removed outdated tracking for: {}".format(beacon['address']))
        else:
            log.debug('Tracking checked and is up to date')

    airfield, at_airfield = detect_airfield(beacon)
    airfield_name = airfield['name'].lower()

    if beacon['address'] not in tracked_aircraft.keys():
        log.debug('Aircraft {} not tracked yet'.format(beacon['address']))
        new_aircraft = AIRCRAFT_DATA_TEMPLATE.copy()

        new_aircraft['airfield'] = airfield_name
        new_aircraft['address'] = beacon['address']
        new_aircraft['address_type'] = beacon['address_type']
        new_aircraft['altitude'] = beacon['altitude']
        new_aircraft['ground_speed'] = beacon['ground_speed']
        new_aircraft['receiver_name'] = beacon['receiver_name']
        new_aircraft['reference_timestamp'] = beacon['reference_timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
        new_aircraft['registration'] = registration

        if beacon['ground_speed'] > 20 and beacon['altitude'] - airfield['elevation'] > 200:
            new_aircraft['status'] = 'air'
        else:
            new_aircraft['status'] = 'ground'
        log.debug("Starting to track aircraft ".format(registration))
        tracked_aircraft[beacon['address']] = new_aircraft
    else:
        log.debug('Updating tracked aircraft')
        aircraft = tracked_aircraft[beacon['address']]
        aircraft['airfield'] = airfield_name

        if beacon['ground_speed'] > 30 and beacon['altitude'] - airfield['elevation'] > 15:
            log.debug("airborne aircraft detected")

            if aircraft['status'] == 'ground' and at_airfield:
                # Aircraft launch detected
                aircraft['status'] = 'air'
                aircraft['takeoff_timestamp'] = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
                aircraft['takeoff_airfield'] = airfield_name
                aircraft['launch_height'] = beacon['altitude'] - airfield['elevation']
                log.info("Adding aircraft {} as launched at {}".format(registration, airfield_name))
                add_flight(db_conn.cursor(), aircraft)
            else:
                # todo detailed launch height calculation
                # - detect aero/winch
                # todo remove unsued aircraft object fields eg 'tracking_launch_height'
                if (aircraft['takeoff_timestamp']):
                    time_since_launch = (beacon['timestamp'] - aircraft['takeoff_timestamp']).total_seconds()
                    log.debug("time since launch: {}".format(time_since_launch))
                    if time_since_launch <= 40:
                        log.debug("Updating aircraft {} launch height".format(aircraft['registration']))
                        log.debug("{} launch height is: {}".format(aircraft['registration'], aircraft['launch_height']))
                        if beacon['altitude'] - airfield['elevation'] > aircraft['launch_height']:
                            aircraft['launch_height'] = beacon['altitude'] - airfield['elevation']
                            update_flight(db_conn.cursor(), aircraft)
                            db_conn.commit()
        elif beacon['ground_speed'] < 20 and beacon['altitude'] - airfield['elevation'] < 15:
            log.debug("aircraft detected on ground")

            if aircraft['status'] == 'air' and at_airfield:
                # Aircraft landing detected
                aircraft['status'] = 'ground'
                aircraft['landing_timestamp'] = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S"))
                aircraft['landing_airfield'] = airfield_name
                log.info("Updating aircraft {} as landed".format(registration))

                if aircraft['takeoff_timestamp']:
                    update_flight(db_conn.cursor(), aircraft)
                    db_conn.commit()
                else:
                    add_flight(db_conn.cursor(), aircraft)
                    db_conn.commit()
                log.info('Aircraft {} flew from {} to {}'.format(aircraft['registration'], aircraft['takeoff_timestamp'], aircraft['landing_timestamp']))
                if aircraft['takeoff_timestamp'] and aircraft['landing_timestamp']:
                    draw_alt_graph(
                        db_conn.cursor(),
                        aircraft,
                        config['TRACKER']['chart_directory']
                    )
                tracked_aircraft.pop(aircraft['address'])

    log.debug('Tracked aircraft =========================')
    log.debug(pprint.pformat(tracked_aircraft))
    log.debug('End Tracked aircraft {} {}'.format(len(tracked_aircraft), '======================'))
    db_conn.close()

def process_beacon(raw_message):
    try:
        beacon = parse(raw_message)
        try:
            if beacon['beacon_type'] in ['aprs_aircraft', 'flarm']:
                log.debug('Aircraft beacon received')
                track_aircraft(beacon, tracked_airfield)
        except KeyError as e:
            log.debug('Beacon type field not found')
            log.debug(e)
            pass
    except ParseError as e:
        log.error('Error, {}'.format(e.message))


log.info('Importing device data')
import_device_data()

log.info("Checking database for active flights")
with make_database_connection() as db_conn:
    database_flights = get_currently_airborne_flights(db_conn.cursor())

tracked_aircraft = {}

for flight in database_flights:
    db_flight = AIRCRAFT_DATA_TEMPLATE.copy()
    db_flight['airfield'] = flight[1]
    db_flight['address'] = flight[2]
    db_flight['address_type'] = flight[3]
    db_flight['altitude'] = flight[4]
    db_flight['ground_speed'] = flight[5]
    db_flight['receiver_name'] = flight[6]
    db_flight['reference_timestamp'] = flight[7]
    db_flight['registration'] = flight[8]
    db_flight['takeoff_timestamp'] = flight[9]
    db_flight['landing_timestamp'] = flight[10]
    db_flight['status'] = flight[11]
    db_flight['tracking_launch_height'] = flight[13]
    db_flight['tracking_launch_start_time'] = flight[14]
    db_flight['launch_height'] = flight[12]
    db_flight['takeoff_airfield'] = flight[15]
    db_flight['landing_airfield'] = flight[16]

    tracked_aircraft[db_flight['address']] = db_flight

log.info("=========")
log.info(pprint.pformat(tracked_aircraft))
log.info("=========")

client = AprsClient(aprs_user='N0CALL', aprs_filter="r/{latitude}/{longitude}/{tracking_radius}".format(tracking_radius=config['TRACKER']['tracking_radius'], **tracked_airfield))
client.connect()
try:
    client.run(callback=process_beacon, autoreconnect=True)
except KeyboardInterrupt:
    print('\nStop ogn gateway')
    client.disconnect()
