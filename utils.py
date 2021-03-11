import configparser
import requests
import json
import logging
import os

import mysql.connector



logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

def make_database_connection(config, retry_counter=0):
    if retry_counter > 5:
        log.error("Failed to connect to database after 5 retries")
        return
    try:
        conn = mysql.connector.connect(
            user=config['TRACKER']['database_user'],
            password=config['TRACKER']['database_password'],
            host=config['TRACKER']['database_host'],
            database=config['TRACKER']['database'])
        return conn
    except mysql.connector.Error as err:
        log.error(err)
        retry_counter += 1
        return make_database_connection(retry_counter)

def import_device_data(config):

    # todo: import to database?
    # todo: keep file for reference?

    # "4054A1": {
    #     "DEVICE_TYPE": "I",
    #     "DEVICE_ID": "4054A1",
    #     "AIRCRAFT_MODEL": "ASK-21",
    #     "REGISTRATION": "G-CHPW",
    #     "CN": "HPW",
    #     "TRACKED": "Y",
    #     "IDENTIFIED": "Y"
    # }

    r = requests.get(config['TRACKER']['device_data_url'])

    if r.status_code != 200:
        log.error('Unable to update device dict: code {}'.format(r.status_code))
        try:
            with open('ogn-ddb.json', 'r') as ddb_data:
                return json.loads(ddb_data.read())
        except FileNotFoundError:
            log.error('No ogn ddb file found')
            return {}

    device_data = r.text

    keys = []
    device_dict = {}

    for line in device_data.splitlines():
        if line[0] == '#':
            keys = line[1:].split(',')
        else:
            values = line.split(',')
            device = {keys[i].strip("'"): values[i].strip("'") for i,key in enumerate(keys)}
            device_dict[device['DEVICE_ID']] = device

    with open('ogn-ddb.json', 'w') as ddb_data:
        ddb_data.write(json.dumps(device_dict))

    return device_dict

def import_beacon_correction_data():
    try:
        with open('beacon-correction-data.json', 'r') as beacon_correction_data:
            return json.loads(beacon_correction_data.read())
    except FileNotFoundError:
        log.error('No ogn beacon correction file found')
        return {}