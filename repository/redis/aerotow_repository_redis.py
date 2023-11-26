import json
import logging
import os
import pprint
import configparser

import redis

from json_utils import json_serial, json_deserial

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def build_aerotow_key(aerotow):
    flight_addresses = sorted(aerotow['flights'])
    return '_'.join(flight_addresses)


def string_to_json(json_str):
    aerotow_dict = json.loads(json_str)
    #Convert becon keys back into ints
    aerotow_dict['beacons'] = {int(key): value for key, value in aerotow_dict['beacons'].items()}
    return aerotow_dict


def json_to_string(areotow):
    try:
        return json.dumps(areotow)
    except TypeError as err:
        log.warning('Type error converting flight to json')
        log.error(pprint.pformat(areotow))
        raise err


class AerotowRepositoryRedis:
    def __init__(self, config):
        self.redis_client = redis.Redis(
            host=config['TRACKER']['redis_host'],
            port=config['TRACKER']['redis_port'],
            db=0,
            decode_responses=True)

        self.config = config

    def add_aerotow(self, aerotow_dict):
        key = build_aerotow_key(aerotow_dict)
        aerotow_dict['aerotow_key'] = key
        self.redis_client.set('flight_tracker_aerotow_' + key, json_to_string(aerotow_dict),
                              ex=int(self.config['TRACKER']['redis_expiry']))
        return key

    def get_aerotow(self, key):
        return string_to_json(self.redis_client.get('flight_tracker_aerotow_' + key))

    def get_all_aerotows(self):
        aerotows = {}
        for cached_aerotow in self.redis_client.scan_iter('flight_tracker_aerotow_*'):
            aerotow = self.redis_client.get(cached_aerotow)
            aerotows[cached_aerotow[-13:]] = string_to_json(aerotow)
        return aerotows

    def get_all_addresses(self):
        return [x[-13:] for x in self.redis_client.scan_iter('flight_tracker_aerotow_*')]

    def update_aerotow(self, aerotow_dict, key=None):
        if not key:
            key = aerotow_dict['aerotow_key']
        return self.redis_client.set('flight_tracker_aerotow_' + key, json_to_string(aerotow_dict),
                                     ex=int(self.config['TRACKER']['redis_expiry']))

    def delete_aerotow(self, key):
        return self.redis_client.delete('flight_tracker_aerotow_' + key)
