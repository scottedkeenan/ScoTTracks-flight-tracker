import configparser
import mysql.connector
import requests
import logging
import os

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_device_data(device_data_url):
    r = requests.get(device_data_url)

    if r.status_code != 200:
        log.error('Unable to update devices: code {}'.format(r.status_code))
        return

    save_data_to_database(r.json())


def save_data_to_database(data):
    # Connect to the database
    db = mysql.connector.connect(
        host=config['TRACKER']['database_host'],
        database=config['TRACKER']['database'],
        user=config['TRACKER']['database_user'],
        password=config['TRACKER']['database_password'],
        port=3307,
        ssl_disabled=True
    )

    # Create a cursor object
    cursor = db.cursor()

    # Create a temporary table to store the new data
    cursor.execute("CREATE TEMPORARY TABLE tmp_aircraft_data LIKE aircraft_data")

    # Insert the new data into the temporary table
    for item in data['devices']:
        tracked = True if item['tracked'] == 'Y' else False
        identified = True if item['identified'] == 'Y' else False
        query = "INSERT INTO tmp_aircraft_data (device_type, device_id, aircraft_model, registration, cn, tracked, identified) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (item['device_type'], item['device_id'], item['aircraft_model'], item['registration'], item['cn'], tracked, identified)
        cursor.execute(query, values)

    # Delete any rows in the main table that are not included in the new data
    cursor.execute("DELETE FROM aircraft_data WHERE DEVICE_ID NOT IN (SELECT DEVICE_ID FROM tmp_aircraft_data)")

    # Copy the new data from the temporary table to the main table
    cursor.execute("REPLACE INTO aircraft_data SELECT * FROM tmp_aircraft_data")

    # Commit the changes to the database
    db.commit()

    # Close the cursor and database connections
    cursor.close()
    db.close()


config = configparser.ConfigParser()
config.read('config.ini')
import_device_data(config['TRACKER']['device_data_url'])
