import configparser
import json
import logging
import os

import pika

from utils import make_database_connection

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import get_filters_by_country_codes
from datetime import date, datetime

config = configparser.ConfigParser()
config.read('config.ini')

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

mq_connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host'], heartbeat=0))
mq_channel = mq_connection.channel()

# beacon_count = 0


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def queue_beacon(beacon):
    # log.info(pprint.pformat(beacon))

    beacon['reference_timestamp'] = json_serial(beacon['reference_timestamp'])
    beacon['timestamp'] = json_serial(beacon['timestamp'])

    beacon_data = json.dumps(beacon)
    mq_channel.basic_publish(exchange='flight_tracker',
                             routing_key='received_beacons',
                             body=beacon_data)


def filter_queue_beacon(raw_message):
    try:
        beacon = parse(raw_message)
        try:
            if beacon['beacon_type'] in ['aprs_aircraft', 'flarm', 'tracker']:
                if beacon['aircraft_type'] in [1, 2, 3, 8]:
                    try:
                        queue_beacon(beacon)
                    except TypeError as e:
                        log.info('Type error while tracking: {}'.format(e))
                else:
                    log.debug("Not a glider or tug")
        except KeyError as e:
            log.debug('Beacon type field not found: {}'.format(e))
    except ParseError as e:
        log.error('Parse error: {}'.format(e))
    except NotImplementedError as e:
        log.error('Not implemented error: {}'.format(e))


# LIVE get beacons
track_countries = config['TRACKER']['track_countries'].split(',')
db_conn = make_database_connection()
if not db_conn:
    exit(1)
filters = get_filters_by_country_codes(db_conn.cursor(), track_countries)
db_conn.close()
aprs_filter = ' '.join(filters)


def connect_to_ogn_and_run(filter_string):
    if len(filter_string.split(' ')) > 9:
        log.error("Too many aprs filters")
    else:
        log.info('Connecting to OGN gateway')
        client = AprsClient(aprs_user='N0CALL', aprs_filter=aprs_filter)
        client.connect()
        try:
            client.run(callback=filter_queue_beacon, autoreconnect=True)
        except KeyboardInterrupt:
            client.disconnect()
            raise
        except AttributeError as err:
            log.error(err)


failures = 0
while failures < 99:
    try:
        connect_to_ogn_and_run(aprs_filter)
    except ConnectionRefusedError as ex:
        log.error('Connection error, retrying')
        log.error(ex)
        failures += 1
    except KeyboardInterrupt:
        log.info('Keyboard interrupt!')
        log.info('Stop OGN gateway')
        break

log.error('Exited with {} failures'.format(failures))


# Debug Get beacons from DB

# comment out the live import above

# from flight_tracker_squirreler import get_filters_by_country_codes, get_raw_beacons_between
#
# db_conn = make_database_connection()
# beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-03-11 10:00:00', '2025-12-22 18:00:00')
# # beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True), '2020-12-29 08:40:55', '2021-12-31 23:00:00')
# # beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True), '2021-02-21 00:00:00', '2022-02-18 23:15:00')
#
# # beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2021-01-03 10:00:00', '2022-01-10 18:00:00')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD51CC', '2020-12-22 15:27:19', '2020-12-22 15:33:15')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD5133', '2020-12-22 15:44:33', '2020-12-22 16:08:56')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DF0D62', '2020-03-07 09:46:00', '2021-03-014 18:00:00')
#
#
# print(len(beacons))
#
# for beacon in beacons:
#     # log.warning(beacon)
#     if beacon['aircraft_type'] in [1,2]:
#         # beacon['timestamp'] = beacon['timestamp'].replace(year=2021, day=1, month=2)
#         # beacon['reference_timestamp'] = beacon['reference_timestamp'].replace(year=2021, day=29, month=1)
#         queue_beacon(beacon)
