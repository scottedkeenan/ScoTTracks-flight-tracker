import time

import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.dates as mdates

from datetime import datetime, timedelta
import json
import tempfile

import boto3
from botocore.exceptions import ClientError

import mysql.connector

import os

from flight_tracker_squirreler import get_beacons_for_address_between

import configparser

import logging

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')


def json_datetime_converter(o):
    if isinstance(o, datetime):
        return o.__str__()


def upload_chart_data_to_s3(cursor, flight_data):
    log.info('Generating graph data')
    # Generate graph of flight

    flight_start_time = datetime.strptime(flight_data['takeoff_timestamp'], '%Y-%m-%d %H:%M:%S')
    flight_end_time = datetime.strptime(flight_data['landing_timestamp'], '%Y-%m-%d %H:%M:%S')
    graph_start_time = (flight_start_time - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    graph_end_time = (flight_end_time + timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    data = get_beacons_for_address_between(cursor,
                                           flight_data['address'],
                                           graph_start_time,
                                           graph_end_time)
    # Todo: Change key into directory-like format
    # Todo: Front end will also need this update
    s3_key = '{}-{}.json'.format(flight_data['address'], graph_start_time).replace(':', '-').replace(' ', '-')
    log.info(s3_key)
    tempdir = tempfile.gettempdir()
    filename = '{}/{}'.format(tempdir, s3_key)
    if data:
        with open(filename, 'w') as f:
            data_dict = {
                'start_time': flight_start_time.strftime("%Y-%m-%d-%H-%M-%S"),
                'address': flight_data['address'],
                'data': data
            }
            f.write(json.dumps(data_dict, default=json_datetime_converter))
        s3_client = boto3.client(
            's3',
            aws_access_key_id=config['AWS']['ACCESS_KEY'],
            aws_secret_access_key=config['AWS']['SECRET_KEY']
        )
        try:
            log.info('Submitting graph data to s3')
            response = s3_client.upload_file(filename, config['AWS']['graph_data_bucket_name'], s3_key)
        except ClientError as e:
            log.error(e)
            return False
        return True
    else:
        log.info('No data to graph found')

# def draw_alt_graph(cursor, aircraft, chart_directory):
#     # Generate graph of flight
#     graph_start_time = (aircraft.takeoff_timestamp - datetime.timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
#     graph_end_time = (aircraft.landing_timestamp + datetime.timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
#     data = get_beacons_for_address_between(cursor,
#                                            aircraft.address,
#                                            graph_start_time,
#                                            graph_end_time)
#     if data:
#         times = []
#         y1 = []
#         y2 = []
#
#         for row in data:
#             times.append((row[0]))
#             y1.append((float(row[1])))
#             y2.append((float(row[2])))
#
#         time_num = matplotlib.dates.date2num(times)
#
#         ax = plt.gca()
#
#         myFmt = mdates.DateFormatter('%H:%M')
#         ax.xaxis.set_major_formatter(myFmt)
#
#         locator = mdates.DayLocator()
#         ax.xaxis.set_major_locator(locator)
#
#         plt.plot_date(time_num, y1, linestyle='-', linewidth=1.0, label='Altitude', marker='.', ms = 3, mec = 'r', mfc = 'r')
#         plt.plot_date(time_num, y2, linestyle='-', linewidth=1.0, label='Ground Speed', marker='.', ms = 3, mec = 'r', mfc = 'r')
#         plt.xlabel('time')
#         plt.ylabel('Altitude in m / speed in kph')
#         # plt.title('Interesting Graph\nCheck it out')
#         plt.legend()
#         plt.grid(True)
#         plt.savefig('{}/{}-{}.png'.format(chart_directory,
#                                           aircraft.registration if aircraft.registration != 'UNKNOWN' else aircraft.address ,
#                                           aircraft.takeoff_timestamp.strftime("%Y-%m-%d-%H-%M-%S")))
#
#         plt.clf()
#         plt.cla()
#         plt.close()
#     else:
#         print('No data found')


# def draw_alt_graph_for_address_between(cursor, address, graph_start_time, graph_end_time, chart_directory):
#     # Generate graph of flight
#     # todo  - timedelta(minutes=1)
#     data = get_beacons_for_address_between(cursor,
#                                            address,
#                                            graph_start_time,
#                                            graph_end_time)
#     lowest_alt = 10000000
#     speed = None
#
#     if data:
#         times = []
#         receivers = {}
#         y2 = []
#
#         for row in data:
#             times.append((row['timestamp']))
#             if row['receiver_name'] not in receivers.keys():
#                 receivers[row['receiver_name']] = {
#                     'times': [(row['timestamp'])],
#                     'alts': [(float(row['altitude']))]
#                 }
#             else:
#                 receivers[row['receiver_name']]['alts'].append((float(row['altitude'])))
#                 receivers[row['receiver_name']]['times'].append((row['timestamp']))
#             y2.append((float(row['ground_speed'])))
#
#         import pprint
#         pprint.pprint(receivers)
#
#         time_num = matplotlib.dates.date2num(times)
#
#         ax = plt.gca()
#
#         myFmt = mdates.DateFormatter('%H:%M')
#         ax.xaxis.set_major_formatter(myFmt)
#
#         locator = mdates.DayLocator()
#         ax.xaxis.set_major_locator(locator)
#
#         for r in receivers.keys():
#             plt.plot_date(matplotlib.dates.date2num(receivers[r]['times']), receivers[r]['alts'], linestyle='-', linewidth=0.3, label=r, ms = 0.3, mec = 'r', mfc = 'r')
#         plt.plot_date(time_num, y2, linestyle='-', linewidth=0.3, label='Ground Speed', marker=None)
#         plt.xlabel('time')
#         plt.ylabel('Altitude in m / speed in kph')
#         # plt.title('Interesting Graph\nCheck it out')
#         lgd = plt.legend(bbox_to_anchor=(1.1, 1.1), bbox_transform=ax.transAxes)
#
#         plt.savefig('{}/{}-{}.png'.format(chart_directory,
#                                           address ,
#                                           times[0].strftime("%Y-%m-%d-%H-%M-%S")),
#                     dpi=500,
#                     bbox_extra_artists=(lgd,),
#                     bbox_inches='tight')
#         plt.clf()
#         plt.cla()
#         plt.close()
#
#
#     else:
#         print('No data found')
#
# import configparser
#
# config = configparser.ConfigParser()
# config.read('config.ini')
#
#
# def make_database_connection(retry_counter=0):
#     if retry_counter > 5:
#         return
#     try:
#         conn = mysql.connector.connect(
#             user=config['TRACKER']['database_user'],
#             password=config['TRACKER']['database_password'],
#             host=config['TRACKER']['database_host'],
#             database=config['TRACKER']['database'])
#         return conn
#     except mysql.connector.Error as err:
#         retry_counter += 1
#         return make_database_connection(retry_counter)
#
# db_conn = make_database_connection()
# # data = get_beacons_for_address_between(db_conn.cursor(), '4057F5', '2021-03-05 09:51:11', '2021-03-05 10:26:53')
# # for d in data:
# #     print(d)
#
# def myconverter(o):
#     if isinstance(o, datetime.datetime):
#         return o.__str__()
#
# import json
# # print(json.dumps(data, default = myconverter))
# draw_alt_graph_for_address_between(db_conn.cursor(dictionary=True), 'DDE6DD', '2021-03-05 09:18:00', '2021-03-05 09:45:00', './public_html/graphs/debug')
# # draw_alt_graph_for_address_between(db_conn.cursor(dictionary=True), 'DF0D62', '2021-03-07 10:19:00', '2021-03-07 10:30:00', './public_html/graphs/debug')
