#!/usr/bin/env python

import json
from datetime import datetime, timedelta

import pika
import configparser
import mysql.connector

import flight_tracker_squirreler


def save_beacons_from_queue():

    config = configparser.ConfigParser()
    config.read('/home/scott/PycharmProjects/flight_tracker/config.ini')

    # Connect to the rabbit mq queue

    connection = pika.BlockingConnection(pika.ConnectionParameters(config['TRACKER']['rabbit_mq_host'], heartbeat=0))
    channel = connection.channel()

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

        # create a database connection

        mydb = mysql.connector.connect(
            host=config['TRACKER']['database_host'],
            user=config['TRACKER']['database_user'],
            password=config['TRACKER']['database_password'],
            database=config['TRACKER']['database']
        )

        cursor = mydb.cursor()

        # Bulk upload the messages

        flight_tracker_squirreler.add_many_beacon(cursor, beacons)
        cursor.close()

        # Ack the queue

        for frame in method_frames:
            channel.basic_ack(frame.delivery_tag)

        beacons_processed += len(beacons)

    print('Beacons processed: {}'.format(beacons_processed))


if __name__ == "__main__":
    save_beacons_from_queue()
