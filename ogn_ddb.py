import requests
import logging
import os

from flight_tracker_squirreler import save_device_data_to_database

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def import_device_data(db_conn, device_data_url):
    r = requests.get(device_data_url)

    if r.status_code != 200:
        log.error('Unable to update devices: code {}'.format(r.status_code))
        return

    save_device_data_to_database(db_conn, r.json())

# config = configparser.ConfigParser()
# config.read('config.ini')
#
# # Connect to the database
# db = mysql.connector.connect(
#     host=config['TRACKER']['database_host'],
#     database=config['TRACKER']['database'],
#     user=config['TRACKER']['database_user'],
#     password=config['TRACKER']['database_password'],
#     port=3307,
#     ssl_disabled=True
# )
#
# # Create a cursor object
# cursor = db.cursor(dictionary=True)
#
#
# # import_device_data(cursor, config['TRACKER']['device_data_url'])
#
# # print(get_device_data_by_address(cursor, '01013F'))
#
# # Close the cursor
# cursor.close()
# db.close()
