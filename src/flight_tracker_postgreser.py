# https://info.crunchydata.com/blog/easy-postgresql-10-and-pgadmin-4-setup-with-docker

def create_daily_flights_table(cursor):
    create_table_sql = """
    DROP TABLE IF EXISTS daily_flights;
    
    CREATE TABLE daily_flights (
        id serial PRIMARY KEY,
        airfield varchar, 
        address varchar,
        address_type int,
        altitude float,
        ground_speed float,
        receiver_name varchar,
        reference_timestamp varchar,
        registration varchar,
        takeoff_timestamp varchar,
        landing_timestamp varchar,
        status varchar
    );
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
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""

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
        status = %s
    WHERE address = %s;"""

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
        aircraft_data['address']
    )

    import psycopg2
    try:
        cursor.execute(insert_row_sql, update_row_data)
    except:
        print(cursor._last_executed)

# import psycopg2
# from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
#
# conn = psycopg2.connect(user="postgres", password="postgres", host="172.19.0.3", dbname="flighttrackerdb")
# conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
# cursor = conn.cursor()
#
# create_daily_flights_table(cursor)