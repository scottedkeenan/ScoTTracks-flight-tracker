import configparser

import requests
import logging
import os

from flight_tracker_squirreler import save_device_data_to_database
from utils import make_database_connection

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_device_data(db_conn, device_data_url):
    log.info('Getting device data from OGN')
    r = requests.get(device_data_url)

    if r.status_code != 200:
        log.error('Unable to update devices: code {}'.format(r.status_code))
        return

    device_count = len(r.json()['devices'])

    log.info('Got data from OGN, {} devices found'.format(device_count))

    saved_rows = save_device_data_to_database(db_conn, r.json())

    if saved_rows != device_count:
        log.error('Device count mismatch {} from OGN, {} in database'.format(device_count, saved_rows))
    else:
        log.info('Device data updated')


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Connect to the database
    db = make_database_connection()

    import_device_data(db, config['TRACKER']['device_data_url'])

    # Close the database
    db.close()
