# https://info.crunchydata.com/blog/easy-postgresql-10-and-pgadmin-4-setup-with-docker

from datetime import datetime

import json

def create_daily_flights_table(cursor):
    create_table_sql = """
    DROP TABLE IF EXISTS daily_flights;
    
    CREATE TABLE `daily_flights` (
        `id` INT PRIMARY KEY AUTO_INCREMENT,
        `airfield` varchar(255) DEFAULT NULL,
        `address` varchar(255) DEFAULT NULL,
        `address_type` int(11) DEFAULT NULL,
        `altitude` float DEFAULT NULL,
        `ground_speed` float DEFAULT NULL,
        `receiver_name` varchar(255) DEFAULT NULL,
        `reference_timestamp` timestamp NULL DEFAULT NULL,
        `registration` varchar(255) DEFAULT NULL,
        `takeoff_timestamp` timestamp NULL DEFAULT NULL,
        `landing_timestamp` timestamp NULL DEFAULT NULL,
        `status` varchar(255) DEFAULT NULL,
        `launch_height` float DEFAULT NULL
    )
    """
    cursor.execute(create_table_sql)


def create_received_beacons_table(cursor):
    create_received_beacons_sql = """
    DROP TABLE IF EXISTS `received_beacons`;
    
    CREATE TABLE `received_beacons`(
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `address` VARCHAR(255) DEFAULT NULL,
    `address_type` INT(11) DEFAULT NULL,
    `aircraft_type` INT(11) DEFAULT NULL,
    `altitude` FLOAT DEFAULT NULL,
    `aprs_type` VARCHAR(255) DEFAULT NULL,
    `beacon_type` VARCHAR(255) DEFAULT NULL,
    `climb_rate` FLOAT DEFAULT NULL,
    `comment` VARCHAR(255) DEFAULT NULL,
    `dstcall` VARCHAR(255) DEFAULT NULL,
    `error_count` INT(11) DEFAULT NULL,
    `flightlevel` INT(11) DEFAULT NULL,
    `frequency_offset` INT(11) DEFAULT NULL,
    `gps_quality` VARCHAR(255) DEFAULT NULL,
    `ground_speed` FLOAT DEFAULT NULL,
    `hardware_version` VARCHAR(255) DEFAULT NULL,
    `latitude` FLOAT DEFAULT NULL,
    `longitude` FLOAT DEFAULT NULL,
    `name` VARCHAR(255) DEFAULT NULL,
    `proximity` VARCHAR(255) DEFAULT NULL,
    `raw_message` VARCHAR(255) DEFAULT NULL,
    `real_address` VARCHAR(255) DEFAULT NULL,
    `receiver_name` VARCHAR(255) DEFAULT NULL,
    `reference_timestamp` TIMESTAMP NULL DEFAULT NULL,
    `relay` VARCHAR(255) DEFAULT NULL,
    `signal_power` VARCHAR(255) DEFAULT NULL,
    `signal_quality` VARCHAR(255) DEFAULT NULL,
    `software_version` VARCHAR(255) DEFAULT NULL,
    `stealth` VARCHAR(255) DEFAULT NULL,
    `symbolcode` VARCHAR(255) DEFAULT NULL,
    `symboltable` VARCHAR(255) DEFAULT NULL,
    `timestamp` TIMESTAMP NULL DEFAULT NULL,
    `track` VARCHAR(255) DEFAULT NULL,
    `turn_rate` VARCHAR(255) DEFAULT NULL
    )
    """
    cursor.execute(create_received_beacons_sql)


def get_currently_airborne_flights(cursor):
    get_flights_sql = """
    SELECT * FROM `daily_flights`
    WHERE status = 'air'
    AND date(reference_timestamp) = date(CURDATE())   
    """
    cursor.execute(get_flights_sql)
    return cursor.fetchall()


def add_flight(cursor, aircraft_data):
    insert_row_sql = """
    INSERT INTO daily_flights (
        airfield, 
        address,
        address_type,
        altitude,
        ground_speed,
        receiver_name,
        reference_timestamp,
        registration,
        takeoff_timestamp,
        landing_timestamp,
        status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

    insert_row_data = (
        aircraft_data['airfield'],
        aircraft_data['address'],
        aircraft_data['address_type'],
        aircraft_data['altitude'],
        aircraft_data['ground_speed'],
        aircraft_data['receiver_name'],
        aircraft_data['reference_timestamp'],
        aircraft_data['registration'],
        aircraft_data['takeoff_timestamp'],
        aircraft_data['landing_timestamp'],
        aircraft_data['status']
    )

    cursor.execute(insert_row_sql, insert_row_data)


def add_beacon(cursor, beacon):
    insert_row_sql = """
    INSERT INTO `received_beacons` (
        address,
        address_type,
        aircraft_type,
        altitude,
        aprs_type,
        beacon_type,
        climb_rate,
        comment,
        dstcall,
        error_count,
        flightlevel,
        frequency_offset,
        gps_quality,
        ground_speed,
        hardware_version,
        latitude,
        longitude,
        name,
        proximity,
        raw_message,
        real_address,
        receiver_name,
        reference_timestamp,
        relay,
        signal_power,
        signal_quality,
        software_version,
        stealth,
        symbolcode,
        symboltable,
        timestamp,
        track,
        turn_rate
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

    insert_row_template = {
        'address': None,
        'address_type': None,
        'aircraft_type': None,
        'altitude': None,
        'aprs_type': None,
        'beacon_type': None,
        'climb_rate': None,
        'comment': None,
        'dstcall': None,
        'error_count': None,
        'flightlevel': None,
        'frequency_offset': None,
        'gps_quality': json.dumps,
        'ground_speed': None,
        'hardware_version': None,
        'latitude': None,
        'longitude': None,
        'name': None,
        'proximity': None,
        'raw_message': None,
        'real_address': None,
        'receiver_name': None,
        'reference_timestamp': None,
        'relay': None,
        'signal_power': None,
        'signal_quality': None,
        'software_version': None,
        'stealth': None,
        'symbolcode': None,
        'symboltable': None,
        'timestamp': None,
        'track': None,
        'turn_rate': None
    }

    insert_row_data = []
    for k, v in insert_row_template.items():
        try:
            if v:
                insert_row_data.append(v(beacon[k]))
            else:
                insert_row_data.append(beacon[k])
        except KeyError:
            print("Key {} not found in beacon".format(k))
            insert_row_data.append(None)
    cursor.execute(insert_row_sql, insert_row_data)


def update_flight(cursor, aircraft_data):
    insert_row_sql = """
    UPDATE daily_flights SET
        airfield = %s, 
        address = %s,
        address_type = %s,
        altitude = %s,
        ground_speed = %s,
        receiver_name = %s,
        reference_timestamp = %s,
        registration = %s,
        takeoff_timestamp = %s,
        landing_timestamp = %s,
        status = %s,
        launch_height = %s
    WHERE address = %s AND takeoff_timestamp = %s;"""

    update_row_data = (
        aircraft_data['airfield'],
        aircraft_data['address'],
        aircraft_data['address_type'],
        aircraft_data['altitude'],
        aircraft_data['ground_speed'],
        aircraft_data['receiver_name'],
        aircraft_data['reference_timestamp'],
        aircraft_data['registration'],
        aircraft_data['takeoff_timestamp'],
        aircraft_data['landing_timestamp'],
        aircraft_data['status'],
        aircraft_data['launch_height'],
        aircraft_data['address'],
        aircraft_data['takeoff_timestamp']
    )

    cursor.execute(insert_row_sql, update_row_data)


def get_beacons_for_flight(cursor, start_datetime, end_datetime):
    get_beacons_sql = """
    SELECT timestamp, altitude, ground_speed
    FROM `received_beacons`
    WHERE reference_timestamp
    BETWEEN '%s AND '%s'
    """
    get_beacons_data = (start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()


def get_beacons_for_address_between(cursor, address, start_datetime, end_datetime):
    print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT timestamp, altitude, ground_speed
    FROM `received_beacons`
    WHERE address = %s
    AND reference_timestamp
    BETWEEN %s AND %s
    """
    get_beacons_data = (address, start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()

def get_beacons_between(cursor, start_datetime, end_datetime):
    print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT timestamp, altitude, ground_speed
    FROM `received_beacons`
    WHERE reference_timestamp
    BETWEEN %s AND %s
    """
    get_beacons_data = (start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()
    # BETWEEN '2020-12-01 15:02:55' AND '2020-12-01 15:09:55'