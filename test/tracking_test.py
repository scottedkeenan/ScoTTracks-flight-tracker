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

from flight_tracker import track_aircraft

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

log.debug("here")

config = configparser.ConfigParser()
config.read('../config.ini')


def make_database_connection():
    conn = mysql.connector.connect(
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        host=config['TRACKER']['database_host'],
        database = config['TRACKER']['database'])
    return conn

from flight_tracker_squirreler import get_raw_beacons_between

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