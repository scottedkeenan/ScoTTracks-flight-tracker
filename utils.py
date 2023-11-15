import configparser
import json
import logging
import os
from datetime import datetime, date

import mysql.connector


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def make_database_connection(retry_counter=0):
    if retry_counter > 5:
        log.error("Failed to connect to database after 5 retries")
        return
    config = configparser.ConfigParser()
    config.read('./config.ini')
    try:
        conn = mysql.connector.connect(
            user=config['TRACKER']['database_user'],
            password=config['TRACKER']['database_password'],
            host=config['TRACKER']['database_host'],
            database=config['TRACKER']['database'],
            port=config['TRACKER']['database_port'],
            ssl_disabled=True if config['TRACKER']['database_ssl_disabled'] == 'True' else False
        )
        return conn
    except mysql.connector.Error as err:
        log.error(err)
        retry_counter += 1
        return make_database_connection(retry_counter)


def import_beacon_correction_data():
    try:
        with open('beacon-correction-data.json', 'r') as beacon_correction_data:
            return json.loads(beacon_correction_data.read())
    except FileNotFoundError:
        log.error('No ogn beacon correction file found')
        return {}


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def json_deserial(timestamp_str):
    return datetime.fromisoformat(timestamp_str)
