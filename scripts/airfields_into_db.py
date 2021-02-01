import configparser
import json

config = configparser.ConfigParser()
config.read('../config.ini')

print("INSERT INTO `airfields` (`name`, `nice_name`, `latitude`, `longitude`, `elevation`) VALUES ")

for airfield in config['AIRFIELDS']:
    airfield_json = json.loads(config['AIRFIELDS'][airfield])

    sql_string = "('{}', '{}', {}, {}, {})".format(
        airfield,
        airfield_json['name'],
        airfield_json['latitude'],
        airfield_json['longitude'],
        airfield_json['elevation']
    )

    print(sql_string + ",")


# def make_database_connection():
#     conn = mysql.connector.connect(
#         user=config['TRACKER']['database_user'],
#         password=config['TRACKER']['database_password'],
#         host=config['TRACKER']['database_host'],
#         database = config['TRACKER']['database'])
#     return conn
#
# from flight_tracker_squirreler import get_raw_beacons_between
#
# db_conn = make_database_connection()
# beacons = get_raw_beacons_between(db_conn.cursor(dictionary=True),'2020-12-24 07:00:00', '2020-12-24 18:00:00')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD51CC', '2020-12-22 15:27:19', '2020-12-22 15:33:15')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), 'DD5133', '2020-12-22 15:44:33', '2020-12-22 16:08:56')
# # beacons = get_raw_beacons_for_address_between(db_conn.cursor(dictionary=True), '405612', '2020-12-22 15:35:59', '2020-12-22 15:52:17')
#
#
# print(len(beacons))
#
# for beacon in beacons:
#     # log.warning(beacon)
#     beacon['address'] = beacon['address']
#     track_aircraft(beacon, save_beacon=False)