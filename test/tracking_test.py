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

config = configparser.ConfigParser()
config.read('./config.ini')


def make_database_connection():
    conn = mysql.connector.connect(
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        host=config['TRACKER']['database_host'],
        database = config['TRACKER']['database'])
    return conn

# 4062D7 	09:24:09 	air 	13:32:18
db_conn = make_database_connection()
beacons = get_beacons_for_address_between(db_conn.cursor(dictionary=True), '4062D7', '2020-12-27 09:24:09', '2020-12-27 13:32:18')



for beacon in beacons:
    print(beacon)