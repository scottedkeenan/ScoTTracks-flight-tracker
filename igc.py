from flight_tracker_squirreler import get_igc_data_for_address_between
import mysql.connector

import json
import configparser
import logging
import os

config = configparser.ConfigParser()
config.read('config.ini')

tracked_airfield_name = config['TRACKER']['tracked_airfield']
tracked_airfield = json.loads(config['AIRFIELDS'][tracked_airfield_name])

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

def make_database_connection():
    conn = mysql.connector.connect(
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        host=config['TRACKER']['database_host'],
        database = config['TRACKER']['database'])
    return conn


import re

def extract_gps_lat_long(target):
    PATTERN_APRS = re.compile(
        r"^(?P<callsign>.+?)>(?P<dstcall>[A-Z0-9]+),((?P<relay>[A-Za-z0-9]+)\*)?.*,(?P<receiver>.+?):(?P<aprs_type>(.))(?P<aprs_body>.*)$")
    PATTERN_APRS_POSITION = re.compile(
        r"^(?P<time>(([0-1]\d|2[0-3])[0-5]\d[0-5]\dh|([0-2]\d|3[0-1])([0-1]\d|2[0-3])[0-5]\dz))(?P<latitude>9000\.00|[0-8]\d{3}\.\d{2})(?P<latitude_sign>N|S)(?P<symbol_table>.)(?P<longitude>18000\.00|1[0-7]\d{3}\.\d{2}|0\d{4}\.\d{2})(?P<longitude_sign>E|W)(?P<symbol>.)(?P<course_extension>(?P<course>\d{3})/(?P<ground_speed>\d{3}))?/(A=(?P<altitude>(-\d{5}|\d{6})))?(?P<pos_extension>\s!W((?P<latitude_enhancement>\d)(?P<longitude_enhancement>\d))!)?(?:\s(?P<comment>.*))?$")

    match = re.search(PATTERN_APRS, target)
    aprs_type = 'position' if match.group('aprs_type') == '/' else 'status' if match.group(
        'aprs_type') == '>' else 'unknown'
    aprs_body = match.group('aprs_body')
    if aprs_type == 'position':
        match_position = re.search(PATTERN_APRS_POSITION, aprs_body)
        lat = (match_position.group('latitude') + (
                    match_position.group('latitude_enhancement') or '0') + match_position.group(
            'latitude_sign')).replace('.', '')
        long = (match_position.group('longitude') + (
                    match_position.group('longitude_enhancement') or '0') + match_position.group(
            'longitude_sign')).replace('.', '')

        return lat, long


def generate_igc(address, start_timestamp, end_timestamp):
    conn = make_database_connection()
    cursor = conn.cursor(dictionary=True)

    data = get_igc_data_for_address_between(cursor, address, start_timestamp, end_timestamp)

    igc_header ="""AXFWA1978
HFDTE020820
HFFXA100
HFPLTPILOTINCHARGE:
HFGTYGLIDERTYPE:
HFGIDGLIDERID:
HFDTM100GPSDATUM:WGS-1984
HFRFWFIRMWAREVERSION:1.1.0.0
HFRHWHARDWAREVERSION:200
HFFTYFRTYPE:flyWithCE FR300
HFGPS:3
HFPRSPRESSALTSENSOR:0
I013638GSP
LXFWGPS01978010403000200100"""

    with open('./igcfile.igc', 'w') as igc_file:

        igc_file.write(igc_header + '\n')

        for row in cursor:

            lat, long = extract_gps_lat_long(row['raw_message'])
            data = {
                'time': row['timestamp'].strftime("%H%M%S"),
                'lat': lat,
                'long': long,
                'gps_alt': '000000'
                # 'gps_alt': str(row['altitude']).replace('.', '')
            }
            igc_line = 'B{time}{lat}{long}A0{gps_alt}{gps_alt}'.format(**data)
            # igc_line = 'B{time}|{lat}|{long}|A|{gps_alt}|{gps_alt}'.format(**data)
            igc_file.write(igc_line + '\n')


generate_igc('DD5133', '2020-12-27 12:59:51', '2020-12-27 13:19:38')