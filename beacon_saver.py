#!/usr/bin/env python

import json
from datetime import datetime, timedelta

import pika
import configparser
import mysql.connector

import flight_tracker_squirreler

from charts import upload_chart_data_to_s3

config = configparser.ConfigParser()
config.read('./config.ini')

# Connect to the rabbit mq queue

connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host'], heartbeat=0))
channel = connection.channel()

# create a database connection

mydb = mysql.connector.connect(
    host=config['TRACKER']['database_host'],
    user=config['TRACKER']['database_user'],
    password=config['TRACKER']['database_password'],
    database=config['TRACKER']['database']
)


def save_beacons_from_queue():

    beacons_processed = 0

    start_time = datetime.now()
    end_timedelta = timedelta(minutes=1)

    messages_found_last_time = True

    print('Starting to save queued beacons')

    while (datetime.now() < start_time + end_timedelta) and messages_found_last_time:

        # get a load of messages (how many?)

        beacons = []
        method_frames = []

        for i in range(1000):
            method_frame, header_frame, message = channel.basic_get(queue='beacons_to_save',
                              auto_ack=False)
            if message and method_frame:
                beacons.append(json.loads(message))
                method_frames.append(method_frame)
            else:
                messages_found_last_time = False
                break

        cursor = mydb.cursor()

        # Bulk upload the messages

        flight_tracker_squirreler.add_many_beacon(cursor, beacons)
        cursor.close()

        # Ack the queue

        for frame in method_frames:
            channel.basic_ack(frame.delivery_tag)

        beacons_processed += len(beacons)

    print('Beacons processed: {}'.format(beacons_processed))


def draw_alt_graph():

    # Consume charts_to_draw queue
    # https://pika.readthedocs.io/en/stable/examples/blocking_basic_get.html

    charts_processed = 0

    start_time = datetime.now()
    end_timedelta = timedelta(minutes=1)

    messages_found_last_time = True

    print('Starting to generate graph data')

    while (datetime.now() < start_time + end_timedelta) and messages_found_last_time:

        # get a load of messages (how many?)

        flights = []
        method_frames = []

        for i in range(25):
            method_frame, header_frame, message = channel.basic_get(queue='charts_to_draw',
                                                                    auto_ack=False)
            if message and method_frame:
                flights.append(json.loads(message))
                method_frames.append(method_frame)
            else:
                messages_found_last_time = False
                print('No messages found this time')
                break

        # Get the chart data and upload to S3

        for flight in flights:
            upload_chart_data_to_s3(mydb.cursor(), flight)

        # Ack the queue

        for frame in method_frames:
            channel.basic_ack(frame.delivery_tag)

        charts_processed += len(flights)

    print('Charts processed: {}'.format(charts_processed))


if __name__ == "__main__":
    save_beacons_from_queue()
    draw_alt_graph()
