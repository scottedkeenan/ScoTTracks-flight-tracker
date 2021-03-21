import configparser
import requests
import json
from math import radians, cos, sin, asin, sqrt
import logging
import os

import pprint

import mysql.connector

# from ogn.client import AprsClient
# from ogn.parser import parse, ParseError
#
from flight_tracker_squirreler import get_active_airfields_for_countries, add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between
#
# from charts import draw_alt_graph
#
# from datetime import datetime, timezone, timedelta
#
# from geopy import distance as measure_distance
#
# from flight_tracker import track_aircraft

from scipy.spatial import kdtree
from geopy import distance as measure_distance


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

log.info("here")
print('here')

config = configparser.ConfigParser()
config.read('../config.ini')


def make_database_connection():
    conn = mysql.connector.connect(
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        host=config['TRACKER']['database_host'],
        database = config['TRACKER']['database'])
    return conn

from flight_tracker_squirreler import get_raw_beacons_between, get_raw_beacons_for_address_between

db_conn = make_database_connection()
# beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-24 07:00:00', '2020-12-24 18:00:00')
beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DF0D62', '2021-03-07 10:19:00', '2021-03-07 10:30:00')
# beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD5133', '2020-12-22 15:44:33', '2020-12-22 16:08:56')
# beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), '405612', '2020-12-22 15:35:59', '2020-12-22 15:52:17')

AIRFIELD_DATA = {}
for airfield in get_active_airfields_for_countries(db_conn.cursor(), config['TRACKER']['track_countries'].split(',')):
    airfield_json = {
        'id': airfield[0],
        'name': airfield[1],
        'nice_name': airfield[2],
        'latitude': airfield[3],
        'longitude': airfield[4],
        'elevation': airfield[5],
        'launch_type_detection': True if airfield[8] == 1 else False
    }
    AIRFIELD_DATA[(airfield_json['latitude'], airfield_json['longitude'])] = airfield_json

AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
log.debug('Airfields loaded: {}'.format(pprint.pformat(AIRFIELD_LOCATIONS)))
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)

db_conn.close()


def detect_airfield(beacon):
    """
    :param beacon:
    :param type:
    :return:
    """
    detection_radius = float(config['TRACKER']['airfield_detection_radius'])


    # If not, detect the nearest airfield and update the flight
    _, closest_airfield_index = AIRFIELD_TREE.query((float(beacon['latitude']), float(beacon['longitude'])), 1)
    closest_airfield = AIRFIELD_DATA[AIRFIELD_LOCATIONS[closest_airfield_index]]
    distance_to_nearest = measure_distance.distance(
        [float(closest_airfield['latitude']), float(closest_airfield['longitude'])],
        (beacon['latitude'], beacon['longitude'])).km
    log.debug(("nearest is: {} at {} with elevation of {}".format(closest_airfield['name'], distance_to_nearest, closest_airfield['elevation'])))
    return closest_airfield['nice_name'], distance_to_nearest, closest_airfield['elevation']

status = None
last_flight_timestamp = None


def agl(nh, fe):
    return nh - fe

log.info(len(beacons))


for beacon in beacons:

    log.info('ALT: {}'.format(beacon['altitude']))

    if last_flight_timestamp:
        log.info(last_flight_timestamp <= beacon['timestamp'])

    log.info('='*10)
    log.info(beacon['timestamp'])
    log.info(status)
    closest, dist, elevation = detect_airfield(beacon)

    log.info('ELEV: {}'.format(elevation))
    log.info('{},{}'.format(beacon['latitude'], beacon['longitude']))

    takeoff = beacon['ground_speed'] > float(config['TRACKER']['airborne_detection_speed']) \
        and agl(beacon['altitude'], elevation) > float(config['TRACKER']['airborne_detection_agl'])

    landing = beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed']) \
        and agl(beacon['altitude'], elevation) < float(config['TRACKER']['landing_detection_agl']) \
        and dist < float(config['TRACKER']['airfield_detection_radius']) \
        and beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate'])

    if landing:
        status = 'ground'
    elif takeoff:
        status = 'air'

    log.info('Takeoff? {} | Speed: {}, {} | AGL: {}, {} '.format(
        takeoff,
        beacon['ground_speed'], beacon['ground_speed'] > float(config['TRACKER']['landing_detection_speed']),
        agl(beacon['altitude'], elevation), agl(beacon['altitude'], elevation) > float(config['TRACKER']['landing_detection_agl']),
    ))


    log.info('Landing? {} | Speed: {}, {} | AGL: {}, {} | Dist ({}): {} {} | Climb: {} {}'.format(
        landing,
        beacon['ground_speed'], beacon['ground_speed'] < float(config['TRACKER']['landing_detection_speed']),
        agl(beacon['altitude'], elevation), agl(beacon['altitude'], elevation) < float(config['TRACKER']['landing_detection_agl']),
        closest, dist, dist < float(config['TRACKER']['airfield_detection_radius']),
        beacon['climb_rate'], beacon['climb_rate'] < float(config['TRACKER']['landing_detection_climb_rate'])))

    last_flight_timestamp = beacon['timestamp']
