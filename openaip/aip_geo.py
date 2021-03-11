import csv
from itertools import islice
import configparser
import pprint
from scipy.spatial import kdtree
from geopy import distance as measure_distance

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between, get_raw_beacons_between, get_airfields, get_filters_by_country_codes, get_active_sites_for_countries, get_raw_beacons_for_address_between

import xml.etree.ElementTree as ET

import utils

config = configparser.ConfigParser()
config.read('../config.ini')

# print({section: dict(config[section]) for section in config.sections()})

# with open('../openaip/openaip_airports_united_kingdom_gb.cup', 'r') as airport_data:
#
#     # Skip comments at the start
#     # fillet_airport_data = islice(airport_data, 26, None)
#
#     # airport_data_reader = csv.DictReader(fillet_airport_data, delimiter=',', quotechar='"', )
#     # for row in airport_data_reader:
#     #     print(row)

airfield_data_files = [
    'openaip_airports_united_kingdom_gb.aip',
    'openaip_airports_australia_au.aip',
    'openaip_airports_france_fr.aip',
    'openaip_airports_new_zealand_nz.aip'
]


AIRFIELD_DATA = {}

for file_name in airfield_data_files:

    tree = ET.parse(file_name)
    root = tree.getroot()

    for airport in root[0].findall('AIRPORT'):

        runways = []

        for runway in airport.findall('RWY'):
            runways.append(runway.find('NAME').text)

        try:
            icao = "'{}'".format(airport.find('ICAO').text)
        except AttributeError:
            icao = 'null'

        airport_dict = {
            'name': airport.find('NAME').text,
            'country_code': airport.find('COUNTRY').text,
            'icao': icao,
            'latitude': airport.find('GEOLOCATION').find('LAT').text,
            'longitude': airport.find('GEOLOCATION').find('LON').text,
            'elevation': airport.find('GEOLOCATION').find('ELEV').text,
            'type': airport.attrib.get('TYPE'),
            'runways': runways
        }

        # pprint.pprint(airport_dict)
        import json

        print("(null,'{}','{}',{},{},{},{},'{}','{}'),".format(
            airport_dict['name'],
            airport_dict['country_code'],
            airport_dict['icao'],
            airport_dict['latitude'],
            airport_dict['longitude'],
            airport_dict['elevation'],
            airport_dict['type'],
            json.dumps(airport_dict['runways'])
        ))

        AIRFIELD_DATA[(airport_dict['latitude'], airport_dict['longitude'])] = airport_dict

print(len(AIRFIELD_DATA))
print('='*100)

db_conn = utils.make_database_connection(config)
if not db_conn:
    exit(1)

GLIDING_CLUBS = []
for airfield in get_active_sites_for_countries(db_conn.cursor(),
                                                   config['TRACKER']['track_countries'].split(',')):
    airfield_json = {
        'id': airfield[0],
        'name': airfield[1],
        'nice_name': airfield[2],
        'latitude': airfield[3],
        'longitude': airfield[4],
        'elevation': airfield[5],
        'country_code': airfield[6],
        'launch_type_detection': True if airfield[8] == 1 else False
    }
    GLIDING_CLUBS.append(airfield_json)



AIRFIELD_LOCATIONS = [x for x in AIRFIELD_DATA.keys()]
# print('Airfields loaded: {}'.format(pprint.pformat(AIRFIELD_LOCATIONS)))
# pprint.pprint(AIRFIELD_DATA)
AIRFIELD_TREE = kdtree.KDTree(AIRFIELD_LOCATIONS)
db_conn.close()

for club in GLIDING_CLUBS:
    # if club['country_code'] != 'GB':
    #     continue
    # detect the nearest airfield
    _, closest_airfield_index = AIRFIELD_TREE.query((float(club['latitude']), float(club['longitude'])), 1)
    closest_airfield = AIRFIELD_DATA[AIRFIELD_LOCATIONS[closest_airfield_index]]
    distance_to_nearest = measure_distance.distance(
        [float(closest_airfield['latitude']), float(closest_airfield['longitude'])],
        (club['latitude'], club['longitude'])).km
    if distance_to_nearest > 10:
        # print('Flagging {} | {}'.format(club['name'], distance_to_nearest))
        print('UPDATE `sites`')
        print("SET `airfield_name` = null")
        print("WHERE `name` = '{}';".format(club['name']))
        print()
    print('UPDATE `sites`')
    print("SET `airfield_name` = '{}'".format(closest_airfield['name']))
    print("WHERE `name` = '{}';".format(club['name']))
    print()
    # print(("nearest to {} is: {} at {}".format(club['name'], closest_airfield['name'], distance_to_nearest)))
