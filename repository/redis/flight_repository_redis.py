import json
import logging
import os
import pprint

import redis

from json_utils import json_serial, json_deserial

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def string_to_flight(json_str):
    flight = json.loads(json_str)

    try:
        flight['timestamp'] = json_deserial(flight['timestamp'])
    except TypeError as err:
        pass
    try:
        flight['takeoff_timestamp'] = json_deserial(flight['takeoff_timestamp'])
    except TypeError:
        pass
    try:
        flight['landing_timestamp'] = json_deserial(flight['landing_timestamp'])
    except TypeError:
        pass
    return flight


def flight_to_string(flight):
    try:
        flight['timestamp'] = json_serial(flight['timestamp'])
    except TypeError:
        pass
    try:
        flight['takeoff_timestamp'] = json_serial(flight['takeoff_timestamp'])
    except TypeError:
        pass
    try:
        flight['landing_timestamp'] = json_serial(flight['landing_timestamp'])
    except TypeError:
        pass
    try:
        return json.dumps(flight)
    except TypeError as err:
        log.warning('Type error dumping flight json {}'.format(flight))
        log.error(pprint.pformat(flight))
        raise err


class FlightRepositoryRedis:
    def __init__(self, config):
        self.redis_client = redis.Redis(
            host=config['TRACKER']['redis_host'],
            port=config['TRACKER']['redis_port'],
            db=0,
            decode_responses=True)

        self.config = config

    def add_flight(self, address, flight_dict):
        self.add_to_geo(address, flight_dict)
        return self.redis_client.set('flight_tracker_aircraft_' + address, flight_to_string(flight_dict), ex=int(self.config['TRACKER']['redis_expiry']))

    def get_flight(self, address):
        try:
            return string_to_flight(self.redis_client.get('flight_tracker_aircraft_' + address))
        except TypeError:
            log.warning('No flight found for {}'.format(address))
            return None

    def get_all_flights(self):
        flights = {}
        for cached_flight in self.redis_client.scan_iter('flight_tracker_aircraft_*'):
            try:
                flight = self.redis_client.get(cached_flight)
                flights[cached_flight[-6:]] = string_to_flight(flight)
            except TypeError:
                # Flight expired in while processing
                log.warning('No flight found for {}'.format(cached_flight))
                continue
        return flights

    def get_all_addresses(self):
        return [x[-6:] for x in self.redis_client.scan_iter('flight_tracker_aircraft_*')]

    def update_flight(self, flight_dict, address=None):
        if not address:
            address = flight_dict['address']
        self.add_to_geo(address, flight_dict)
        return self.redis_client.set('flight_tracker_aircraft_' + address, flight_to_string(flight_dict), ex=int(self.config['TRACKER']['redis_expiry']))

    def delete_flight(self, address):
        return self.redis_client.delete('flight_tracker_aircraft_' + address)

    def address_exists(self, address):
        return True if self.redis_client.exists('flight_tracker_aircraft_' + address) == 1 else False

    def add_to_geo(self, address, flight_dict):
        # each item or place is formed by the triad longitude, latitude and name.
        if flight_dict['last_longitude'] is not None and flight_dict['last_latitude'] is not None:
            geo_data = [flight_dict['last_longitude'], flight_dict['last_latitude'], address]
            # log.info('Adding this to geoset: {}'.format(geo_data))
            self.redis_client.geoadd('aircraft', geo_data)

    def get_aircraft_in_radius(self, lat, lon, radius=10):
        return [{'geospatial': x, 'aircraft': self.get_flight(x[0])} for x in self.redis_client.georadius('aircraft', lon, lat, radius, 'km', True, True)]
