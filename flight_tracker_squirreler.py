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
        `aircraft_type` int(11) DEFAULT NULL,
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
    SELECT 
    daily_flights.*, 
    tof.id AS takeoff_airfield_id, 
    tof.name AS takeoff_airfield_name, 
    tof.country_code AS takeoff_airfield_country_code, 
    tof.icao AS takeoff_airfield_icao, 
    tof.latitude AS takeoff_airfield_latitude, 
    tof.longitude AS takeoff_airfield_longitude, 
    tof.elevation AS takeoff_airfield_elevation, 
    tof.type AS takeoff_airfield_type, 
    tof.runways AS takeoff_airfield_runways, 
    tof.follow_aircraft AS takeoff_airfield_follow_aircraft,
    nf.id AS takeoff_airfield_id, 
    nf.name AS takeoff_airfield_name, 
    nf.country_code AS takeoff_airfield_country_code, 
    nf.icao AS takeoff_airfield_icao, 
    nf.latitude AS takeoff_airfield_latitude, 
    nf.longitude AS takeoff_airfield_longitude, 
    nf.elevation AS takeoff_airfield_elevation, 
    nf.type AS takeoff_airfield_type, 
    nf.runways AS takeoff_airfield_runways, 
    nf.follow_aircraft AS takeoff_airfield_follow_aircraft,
    sites.nice_name AS takeoff_airfield_nice_name,
    sites.launch_type_detection as takeoff_airfield_launch_type_detection
FROM 
    daily_flights 
    JOIN airfields AS tof ON daily_flights.takeoff_airfield = tof.id 
    JOIN airfields AS nf ON daily_flights.airfield = nf.id 
    LEFT JOIN sites ON sites.airfield_id = tof.id
WHERE 
    status = 'air' 
    AND DATE(reference_timestamp) = DATE(CURDATE()) 
    AND landing_timestamp IS NULL;
    """
    cursor.execute(get_flights_sql)
    return cursor.fetchall()


def add_flight(cursor, aircraft_data):
    insert_row_sql = """
    INSERT INTO daily_flights (
        airfield, 
        address,
        aircraft_type,
        altitude,
        ground_speed,
        receiver_name,
        reference_timestamp,
        registration,
        takeoff_timestamp,
        takeoff_airfield,
        landing_timestamp,
        landing_airfield,
        status,
        launch_height,
        launch_type,
        average_launch_climb_rate,
        max_launch_climb_rate,
        launch_complete,
        tug_registration,
        aircraft_model,
        competition_number
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

    insert_row_data = (
        aircraft_data['nearest_airfield']['name'],
        aircraft_data['address'],
        aircraft_data['aircraft_type'],
        aircraft_data['altitude'],
        aircraft_data['ground_speed'],
        aircraft_data['receiver_name'],
        aircraft_data['timestamp'],
        aircraft_data['registration'],
        aircraft_data['takeoff_timestamp'],
        aircraft_data['takeoff_airfield']['id'] if aircraft_data['takeoff_airfield'] else None,
        aircraft_data['landing_timestamp'],
        aircraft_data['landing_airfield']['id'] if aircraft_data['landing_airfield'] else None,
        aircraft_data['status'],
        aircraft_data['launch_height'],
        aircraft_data['launch_type'],
        aircraft_data['average_launch_climb_rate'],
        aircraft_data['max_launch_climb_rate'],
        aircraft_data['launch_complete'],
        aircraft_data['tug'],
        aircraft_data['aircraft_model'],
        aircraft_data['competition_number']
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
            # print("Key {} not found in beacon".format(k))
            insert_row_data.append(None)
    cursor.execute(insert_row_sql, insert_row_data)


def add_many_beacon(cursor, data):
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
    for beacon in data:
        # print(beacon)
        # print(type(beacon))
        row = []
        for k, v in insert_row_template.items():
            try:
                if v:
                    row.append(v(beacon[k]))
                else:
                    row.append(beacon[k])
            except KeyError:
                # print("Key {} not found in beacon".format(k))
                row.append(None)
        insert_row_data.append(tuple(row))
    cursor.executemany(insert_row_sql, insert_row_data)


def update_flight(cursor, aircraft_data):
    insert_row_sql = """
    UPDATE daily_flights SET
        airfield = %s, 
        address = %s,
        aircraft_type = %s,
        altitude = %s,
        ground_speed = %s,
        receiver_name = %s,
        reference_timestamp = %s,
        registration = %s,
        takeoff_timestamp = %s,
        takeoff_airfield = %s,
        landing_timestamp = %s,
        landing_airfield = %s,
        status = %s,
        launch_height = %s,
        launch_type = %s,
        average_launch_climb_rate = %s,
        max_launch_climb_rate = %s,
        launch_complete = %s,
        tug_registration = %s
    WHERE address = %s AND takeoff_timestamp = %s;"""

    update_row_data = (
        aircraft_data['nearest_airfield']['name'],
        aircraft_data['address'],
        aircraft_data['aircraft_type'],
        aircraft_data['altitude'],
        aircraft_data['ground_speed'],
        aircraft_data['receiver_name'],
        aircraft_data['timestamp'],
        aircraft_data['registration'],
        aircraft_data['takeoff_timestamp'],
        aircraft_data['takeoff_airfield']['id'] if aircraft_data['takeoff_airfield'] else None,
        aircraft_data['landing_timestamp'],
        aircraft_data['landing_airfield']['id'] if aircraft_data['landing_airfield'] else None,
        aircraft_data['status'],
        aircraft_data['launch_height'],
        aircraft_data['launch_type'],
        aircraft_data['average_launch_climb_rate'],
        aircraft_data['max_launch_climb_rate'],
        aircraft_data['launch_complete'],
        aircraft_data['tug'],

        aircraft_data['address'],
        aircraft_data['takeoff_timestamp']
    )

    cursor.execute(insert_row_sql, update_row_data)


def get_todays_flights(cursor):
    get_flights_sql = """
    SELECT * FROM `daily_flights`
    WHERE DATE(`takeoff_timestamp`) = CURDATE()
    ORDER BY id
    """
    get_flights_data = (datetime.now().strftime("%Y-%m-%d"))
    cursor.execute(get_flights_sql, get_flights_data)
    return cursor.fetchall()


def get_all_flights(cursor):
    get_flights_sql = """
    SELECT * FROM `daily_flights`
    ORDER BY id DESC
    """
    cursor.execute(get_flights_sql, )
    return cursor.fetchall()


def get_raw_beacons_for_address_between(cursor, address, start_datetime, end_datetime):
    # print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT * FROM `received_beacons`
    WHERE address = %s
    AND timestamp BETWEEN %s AND %s
    ORDER BY id
    """
    get_beacons_data = (address, start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()


def get_beacons_for_address_between(cursor, address, start_datetime, end_datetime):
    # print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT timestamp, altitude, ground_speed, receiver_name, latitude, longitude
    FROM `received_beacons`
    WHERE address = %s
    AND timestamp BETWEEN %s AND %s
    GROUP BY (timestamp)
    ORDER BY timestamp;
    """
    get_beacons_data = (address, start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()


def get_igc_data_for_address_between(cursor, address, start_datetime, end_datetime):
    # print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT timestamp, raw_message, altitude
    FROM `received_beacons`
    WHERE address = %s
    AND timestamp BETWEEN %s AND %s
    ORDER BY timestamp
    """
    get_beacons_data = (address, start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor

def get_raw_beacons_between(cursor, start_datetime, end_datetime):
    # print("Getting beacons between {} and {}".format(start_datetime, end_datetime))
    get_beacons_sql = """
    SELECT *
    FROM `received_beacons`
    WHERE timestamp BETWEEN %s AND %s
    ORDER by id
    """
    get_beacons_data = (start_datetime, end_datetime)

    cursor.execute(get_beacons_sql, get_beacons_data)
    return cursor.fetchall()


def get_airfields(cursor):
    get_airfields_sql = """
    SELECT *
    FROM `airfields`
    """
    cursor.execute(get_airfields_sql)
    return cursor.fetchall()


def get_airfields_for_countries(cursor, country_codes):
    placeholder = '%s'
    placeholders = ', '.join(placeholder for unused in country_codes)

    get_airfields_sql = """
    SELECT airfields.*, sites.nice_name, sites.launch_type_detection
    FROM airfields
    LEFT JOIN sites
    ON airfields.id = sites.airfield_id
    WHERE airfields.country_code IN ({})
    """.format(placeholders)

    cursor.execute(get_airfields_sql, country_codes)
    return cursor.fetchall()

def get_sites(cursor):
    get_sites_sql = """
    SELECT *
    FROM `sites`
    """
    cursor.execute(get_sites_sql)
    return cursor.fetchall()


def get_sites_with_no_airfield(cursor):
    get_sites_sql = """
    SELECT *
    FROM `sites`
    WHERE `airfield_name` IS NULL;
    """
    cursor.execute(get_sites_sql)
    return cursor.fetchall()


def get_airfields_sites_for_countries(cursor, country_codes):
    placeholder = '%s'
    placeholders = ', '.join(placeholder for unused in country_codes)

    get_sites_sql = """
    SELECT * FROM sites
    LEFT JOIN airfields ON airfields.name = sites.airfield_name
    WHERE `sites`.country_code IN ({0})
    UNION
    SELECT * FROM sites
    RIGHT JOIN airfields ON airfields.name = sites.airfield_name
    WHERE `sites`.country_code IN ({0})  
    """.format(placeholders)

    cursor.execute(get_sites_sql, country_codes + country_codes)
    return cursor.fetchall()


def get_active_sites_for_countries(cursor, country_codes):
    placeholder = '%s'
    placeholders = ', '.join(placeholder for unused in country_codes)

    get_sites_sql = """
    SELECT * FROM `sites` 
    LEFT JOIN airfields ON sites.airfield_name=airfields.name
    WHERE is_active = TRUE
    AND sites.country_code IN (%s)
    """ % placeholders

    cursor.execute(get_sites_sql, country_codes)
    return cursor.fetchall()


def get_filters_by_country_codes(cursor, country_codes):
    placeholder = '%s'
    placeholders = ', '.join(placeholder for unused in country_codes)

    get_filters_sql = """
    SELECT aprs_filter
    FROM `countries`
    WHERE country_code IN (%s);
    """ % placeholders

    cursor.execute(get_filters_sql, country_codes)
    return [i[0] for i in cursor.fetchall()]


def get_device_data_by_address(cursor, address):

    get_device_data_sql = """
    SELECT *
    FROM `device_data`
    WHERE `device_id` = %s
    LIMIT 1;
    """
    cursor.execute(get_device_data_sql, [address])
    return cursor.fetchone()


def save_device_data_to_database(db_conn, data):

    cursor = db_conn.cursor()

    # Create a temporary table to store the new data
    cursor.execute("CREATE TEMPORARY TABLE tmp_device_data LIKE device_data")

    # Insert the new data into the temporary table
    for item in data['devices']:
        tracked = True if item['tracked'] == 'Y' else False
        identified = True if item['identified'] == 'Y' else False
        query = "INSERT INTO tmp_device_data (device_type, device_id, aircraft_model, registration, cn, tracked, identified) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (item['device_type'], item['device_id'], item['aircraft_model'], item['registration'], item['cn'], tracked, identified)
        cursor.execute(query, values)

    # Delete any rows in the main table that are not included in the new data
    cursor.execute('DELETE FROM device_data WHERE DEVICE_ID NOT IN (SELECT DEVICE_ID FROM tmp_device_data)')

    # Copy the new data from the temporary table to the main table
    cursor.execute('REPLACE INTO device_data SELECT * FROM tmp_device_data')

    db_conn.commit()
    cursor.execute('SELECT count(*) from device_data')
    device_count = cursor.fetchone()[0]
    cursor.close()
    return device_count
