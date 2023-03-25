import configparser

import requests
import logging
import os

from flight_tracker_squirreler import save_device_data_to_database
from utils import make_database_connection

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_device_data(db_conn, device_data_url):
    r = requests.get(device_data_url)

    if r.status_code != 200:
        log.error('Unable to update devices: code {}'.format(r.status_code))
        return

    save_device_data_to_database(db_conn, r.json())

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Connect to the database
    db = make_database_connection()

    # Create a cursor object
    cursor = db.cursor(dictionary=True)

    import_device_data(cursor, config['TRACKER']['device_data_url'])

    # Close the cursor
    cursor.close()
    db.close()
