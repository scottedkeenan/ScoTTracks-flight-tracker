# https://info.crunchydata.com/blog/easy-postgresql-10-and-pgadmin-4-setup-with-docker

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


import mysql.connector

conn = mysql.connector.connect(user="scottedk_ogn", password="rategood13", host="91.238.163.173", database="scottedk_ogn_logs")
cursor = conn.cursor()
# create_daily_flights_table(cursor)

print(cursor.execute("SHOW TABLES"))
