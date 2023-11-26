import json
import logging
import os
import pprint
import configparser

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

    # log.warning(pprint.pformat(flight))
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
        log.warning('CNUT')
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
        return self.redis_client.set('flight_tracker_aircraft_' + address, flight_to_string(flight_dict), ex=int(self.config['TRACKER']['redis_expiry']))


    def get_flight(self, address):
        return string_to_flight(self.redis_client.get('flight_tracker_aircraft_' + address))

    def get_all_flights(self):
        flights = {}
        for cached_flight in self.redis_client.scan_iter('flight_tracker_aircraft_*'):
            flight = self.redis_client.get(cached_flight)
            flights[cached_flight[-6:]] = string_to_flight(flight)
        return flights

    def get_all_addresses(self):
        return [x[-6:] for x in self.redis_client.scan_iter('flight_tracker_aircraft_*')]

    def update_flight(self, flight_dict, address=None):
        if not address:
            address = flight_dict['address']
        # log.info('Updating flight {}'.format(address))
        return self.redis_client.set('flight_tracker_aircraft_' + address, flight_to_string(flight_dict), ex=int(self.config['TRACKER']['redis_expiry']))

    def delete_flight(self, address):
        return self.redis_client.delete('flight_tracker_aircraft_' + address)

    def address_exists(self, address):
        return True if self.redis_client.exists('flight_tracker_aircraft_' + address) == 1 else False
