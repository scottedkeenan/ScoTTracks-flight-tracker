import requests
import json
from math import radians, cos, sin, asin, sqrt

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_postgreser import add_flight, update_flight



UKDRL = {'longitude': -0.854433, 'latitude': 53.248563}
UKNHL = {'longitude': -0.854433, 'latitude': 53.248563}
PORTMOAK = {'name': 'Portmoak', 'latitude': 56.188496, 'longitude': -3.321460, 'elevation': 109.728}
ROCKTON = {'name': 'Rockton', 'latitude': 43.322222, 'longitude': -80.176389, 'elevation': 258}
RIDEAU = {'name': 'Rideau', 'latitude': 45.100788, 'longitude': -75.632947, 'elevation': 87}
TRUCKEE = {'name': 'Truckee', 'latitude': 39.321262, 'longitude': -120.139830, 'elevation': 1799}

AIRCRAFT_DATA_TEMPLATE = {
        'airfield': None,
        'address': None,
        'address_type': None,
        'altitude': None,
        'ground_speed': None,
        'receiver_name': None,
        'reference_timestamp': None,
        'registration': None,
        'takeoff_timestamp': None,
        'landing_timestamp': None,
        'status': None
}

tracked_aircraft = {}

conn = psycopg2.connect(user="postgres", password="postgres", host="172.19.0.3", dbname="flighttrackerdb")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()


def import_device_data():

    device_data = requests.get('http://ddb.glidernet.org/download/').text

    device_dict = {}

    for line in device_data.splitlines():
        if line[0] == '#':
            continue
        else:
            split_line = line.split(',')
            device_dict[split_line[1].strip("'")] = split_line[3].strip("'")

    with open('ogn-ddb.json', 'w') as ddb_data:
        ddb_data.write(json.dumps(device_dict))

    return device_dict


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def track_aircraft(beacon, airfield, distance):

    try:
        with open('ogn-ddb.json') as ogn_ddb:
            device_dict = json.load(ogn_ddb)
    except IOError:
        device_dict = import_device_data()

    try:
        registration = device_dict[beacon['address']]
    except KeyError:
        registration = 'UNKNOWN'

    print('Received {aprs_type} for {registration} {distance} km from {location}. Speed: {ground_speed}, Altitude: {altitude}'.format(
        location=airfield['name'], registration=registration, distance=distance, **beacon))

    if beacon['address'] not in tracked_aircraft.keys():
        print('Aircraft not tracked yet')
        new_aircraft = AIRCRAFT_DATA_TEMPLATE.copy()

        new_aircraft['airfield'] = airfield['name']
        new_aircraft['address'] = beacon['address']
        new_aircraft['address_type'] = beacon['address_type']
        new_aircraft['altitude'] = beacon['altitude']
        new_aircraft['ground_speed'] = beacon['ground_speed']
        new_aircraft['receiver_name'] = beacon['receiver_name']
        new_aircraft['reference_timestamp'] = beacon['reference_timestamp']
        new_aircraft['registration'] = registration


        if beacon['ground_speed'] > 0 and beacon['altitude'] - airfield['elevation'] > 30:
            new_aircraft['status'] = 'air'
        else:
            new_aircraft['status'] = 'ground'

        tracked_aircraft[beacon['address']] = new_aircraft


    else:
        if beacon['ground_speed'] > 0 and beacon['altitude'] - airfield['elevation'] > 30:
            aircraft = tracked_aircraft[beacon['address']]

            aircraft['altitude'] = beacon['altitude']
            aircraft['ground_speed'] = beacon['ground_speed']
            aircraft['receiver_name'] = beacon['receiver_name']
            aircraft['reference_timestamp'] = beacon['reference_timestamp']

            if aircraft['status'] == 'ground':
                aircraft['status'] = 'air'
                aircraft['takeoff_timestamp'] = beacon['timestamp']
                print("Adding aircraft {} as launched".format(registration))
                add_flight(cursor, aircraft)
            # else:
                # check for aircraft in DB
                # if present, update

        if beacon['ground_speed'] < 30 and beacon['altitude'] - airfield['elevation'] < 30:
            aircraft = tracked_aircraft[beacon['address']]

            aircraft['altitude'] = beacon['altitude']
            aircraft['ground_speed'] = beacon['ground_speed']
            aircraft['receiver_name'] = beacon['receiver_name']
            aircraft['reference_timestamp'] = beacon['reference_timestamp']
            aircraft['timestamp'] = beacon['timestamp']

            if aircraft['status'] == 'air':
                aircraft['status'] = 'ground'
                aircraft['landing_timestamp'] = beacon['timestamp']
                # if aircraft in DB
                print("Updating aircraft {} as landed".format(registration))
                update_flight(cursor, aircraft)
                # else add flight (landout)

    print('Tracked aircraft =========================')
    pprint.pprint(tracked_aircraft)
    print('End Tracked aircraft', len(tracked_aircraft), '======================')


def get_distance_from_location(beacon, beacon_location):
    distance = haversine(
        beacon['longitude'],
        beacon['latitude'],
        beacon_location['longitude'],
        beacon_location['latitude']
    )
    return distance

import pprint
def process_beacon(raw_message):
    try:
        beacon = parse(raw_message)
        if 'aircraft_type' in beacon.keys():
            location = TRUCKEE
            distance = get_distance_from_location(beacon, location)
            if distance < 20:
            # if distance < 3.21869:
                pprint.pprint(beacon)
                track_aircraft(beacon, location, distance)
    except ParseError as e:
        print('Error, {}'.format(e.message))


client = AprsClient(aprs_user='N0CALL')
client.connect()
try:
    client.run(callback=process_beacon, autoreconnect=True)
except KeyboardInterrupt:
    print('\nStop ogn gateway')
    client.disconnect()