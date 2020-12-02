import requests
import json
from math import radians, cos, sin, asin, sqrt

import pprint

import mysql.connector

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between

from charts import draw_alt_graph

from datetime import datetime, timezone, timedelta

DARLTON = {'name': 'Darlton', 'longitude': -0.854433, 'latitude': 53.248563, 'elevation': 47}
UKNHL = {'name': 'DSGC', 'longitude': -0.854433, 'latitude': 53.248563}
PORTMOAK = {'name': 'Portmoak', 'latitude': 56.188496, 'longitude': -3.321460, 'elevation': 109.728}
ROCKTON = {'name': 'Rockton', 'latitude': 43.322222, 'longitude': -80.176389, 'elevation': 258}
RIDEAU = {'name': 'Rideau', 'latitude': 45.100788, 'longitude': -75.632947, 'elevation': 87}
TRUCKEE = {'name': 'Truckee', 'latitude': 39.321262, 'longitude': -120.139830, 'elevation': 1799}
SYERSTON = {'name': 'Syerston', 'latitude': 53.024159, 'longitude': -0.911710, 'elevation': 69}
MINDEN = {'name': 'Minden', 'latitude': 32.646111, 'longitude': -93.298056, 'elevation': 85}
WINNIPEG = {'name': 'Winnipeg', 'latitude': 49.705749, 'longitude': -97.680345, 'elevation': 914}
LASHAM = {'name': 'Lasham', 'latitude': 51.186965, 'longitude': -1.033020, 'elevation': 188}
ST_AUBAN = {'name': 'Château-Arnoux-Saint-Auban', 'latitude': 44.06030204989779, 'longitude': 5.9928040471531805, 'elevation': 459}

tracked_airfield = ST_AUBAN

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
    'status': None,
}


def make_database_connection():
    conn = mysql.connector.connect('creds')
    return conn


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


def track_aircraft(beacon, airfield):
    print("track aircraft!")

    db_conn = make_database_connection()

    add_beacon(db_conn.cursor(), beacon)

    try:
        with open('ogn-ddb.json') as ogn_ddb:
            device_dict = json.load(ogn_ddb)
    except IOError:
        device_dict = import_device_data()

    try:
        registration = device_dict[beacon['address']]
    except KeyError:
        registration = 'UNKNOWN'

    if beacon['address'] in tracked_aircraft.keys():
        # Remove outdated tracking
        if datetime.date(tracked_aircraft[beacon['address']]['reference_timestamp']) < datetime.today().date():
            tracked_aircraft.pop(beacon['address'])
            print("Removed outdated tracking for: {}".format(beacon['address']))
        else:
            print('Tracking checked and is up to date')

    print(beacon['address'])
    if beacon['address'] not in tracked_aircraft.keys():
        print('Aircraft not tracked yet')
        new_aircraft = AIRCRAFT_DATA_TEMPLATE.copy()

        new_aircraft['airfield'] = airfield['name']
        new_aircraft['address'] = beacon['address']
        new_aircraft['address_type'] = beacon['address_type']
        new_aircraft['altitude'] = beacon['altitude']
        new_aircraft['ground_speed'] = beacon['ground_speed']
        new_aircraft['receiver_name'] = beacon['receiver_name']
        new_aircraft['reference_timestamp'] = beacon['reference_timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
        new_aircraft['registration'] = registration

        if beacon['ground_speed'] > 30 and beacon['altitude'] - airfield['elevation'] > 200:
            new_aircraft['status'] = 'air'
        else:
            new_aircraft['status'] = 'ground'
        print("Starting to track aircraft ".format(registration))
        tracked_aircraft[beacon['address']] = new_aircraft
    else:
        aircraft = tracked_aircraft[beacon['address']]
        print("=" * 10)
        print("Aircraft {} is {}".format(aircraft['registration'], aircraft['status']))
        print("Aircraft {} speed is {}".format(aircraft['registration'], beacon['ground_speed']))
        print("Aircraft {} altitude is {}".format(aircraft['registration'], beacon['altitude']))
        print("Aircraft {} height is {}".format(aircraft['registration'], beacon['altitude'] - airfield['elevation']))
        print("=" * 10)

        if beacon['ground_speed'] > 30 and beacon['altitude'] - airfield['elevation'] > 15:
            print("airborne aircraft detected")

            if aircraft['status'] == 'ground':
                aircraft['status'] = 'air'
                aircraft['takeoff_timestamp'] = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S")
                aircraft['launch_height'] = beacon['altitude'] - airfield['elevation']
                print("Adding aircraft {} as launched".format(registration))
                print(aircraft)
                add_flight(db_conn.cursor(), aircraft)
                print(db_conn.commit())
            else:
                # todo detailed launch height calculation
                # - detect aero/winch
                # - generate height graph
                # todo remove unsued aircraft object fields eg 'tracking_launch_height'
                if (aircraft['takeoff_timestamp']):
                    time_since_launch = (beacon['timestamp'] - aircraft['takeoff_timestamp']).total_seconds()
                    print("time since launch: {}".format(time_since_launch))
                    if time_since_launch <= 40:
                        print("Updating aircraft {} launch height".format(aircraft['registration']))
                        print("{} launch height is: {}".format(aircraft['registration'], aircraft['launch_height']))
                        if beacon['altitude'] - airfield['elevation'] > aircraft['launch_height']:
                            aircraft['launch_height'] = beacon['altitude'] - airfield['elevation']
                            print("before LH DB")

                            update_flight(db_conn.cursor(), aircraft)
                            print(db_conn.commit())
                            print("after LH DB")


        elif beacon['ground_speed'] < 30 and beacon['altitude'] - airfield['elevation'] < 15:
            print("aircraft detected on ground")

            if aircraft['status'] == 'air':
                aircraft['status'] = 'ground'
                aircraft['landing_timestamp'] = beacon['timestamp']  # .strftime("%m/%d/%Y, %H:%M:%S"))
                print("Updating aircraft {} as landed".format(registration))

                if aircraft['takeoff_timestamp']:
                    update_flight(db_conn.cursor(), aircraft)
                    print(db_conn.commit())
                else:
                    add_flight(db_conn.cursor(), aircraft)
                    print(db_conn.commit())
                pprint.pprint(aircraft)
                print(aircraft['takeoff_timestamp'])
                print('.' * 10)
                print(aircraft['landing_timestamp'])
                if aircraft['takeoff_timestamp'] and aircraft['landing_timestamp']:
                    print("before graph")
                    print("what the fuck")
                    # Generate graph of flight
                    # todo  - timedelta(minutes=1)
                    print(aircraft['takeoff_timestamp'])
                    graph_start_time = aircraft['takeoff_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    print("Graph start time: {}".format(graph_start_time))
                    graph_end_time = aircraft['landing_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    print("Graph end time: {}".format(graph_end_time))
                    data = get_beacons_for_address_between(db_conn.cursor(),
                                                           aircraft['address'],
                                                           graph_start_time,
                                                           graph_end_time)

                    print("Graph data")
                    print(data)

                    draw_alt_graph(
                        aircraft['registration'] if aircraft['registration'] != 'UNKNOWN' else aircraft['address'],
                        data
                    )
                print("after graph")


                tracked_aircraft.pop(aircraft['address'])

    print('Tracked aircraft =========================')
    pprint.pprint(tracked_aircraft)
    print('End Tracked aircraft', len(tracked_aircraft), '======================')
    db_conn.close()


def process_beacon(raw_message):
    print("beacon!")
    try:
        beacon = parse(raw_message)
        # if 'aircraft_type' in beacon.keys():
        try:
            if beacon['beacon_type'] in ['aprs_aircraft', 'flarm']:
                track_aircraft(beacon, tracked_airfield)
        except KeyError as e:
            print(e)
            pass
            print('beacon_type field not found')
            # print(beacon)
    except ParseError as e:
        print('Error, {}'.format(e.message))


print("Checking database for active flights")
with make_database_connection() as db_conn:
    database_flights = get_currently_airborne_flights(db_conn.cursor())


tracked_aircraft = {}

for flight in database_flights:
    db_flight = AIRCRAFT_DATA_TEMPLATE.copy()
    db_flight['airfield'] = flight[1]
    db_flight['address'] = flight[2]
    db_flight['address_type'] = flight[3]
    db_flight['altitude'] = flight[4]
    db_flight['ground_speed'] = flight[5]
    db_flight['receiver_name'] = flight[6]
    db_flight['reference_timestamp'] = flight[7]
    db_flight['registration'] = flight[8]
    db_flight['takeoff_timestamp'] = flight[9]
    db_flight['landing_timestamp'] = flight[10]
    db_flight['status'] = flight[11]
    db_flight['tracking_launch_height'] = flight[13]
    db_flight['tracking_launch_start_time'] = flight[14]
    db_flight['launch_height'] = flight[12]

    tracked_aircraft[db_flight['address']] = db_flight

print("=========")
pprint.pprint(tracked_aircraft)
print("=========")

# if not has_airfield_sun_set(tracked_airfield):
client = AprsClient(aprs_user='N0CALL', aprs_filter="r/{latitude}/{longitude}/5".format(**tracked_airfield))
client.connect()
try:
    client.run(callback=process_beacon, autoreconnect=True)
except KeyboardInterrupt:
    print('\nStop ogn gateway')
    client.disconnect()
