import pprint
from collections import deque
from datetime import datetime
from statistics import mean
import os

import logging

import aerotow_processor

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def new_flight():
    return {
        'nearest_airfield': None,
        'address': None,
        'aircraft_type': None,
        'altitude': None,
        'ground_speed': None,
        'receiver_name': None,
        'timestamp': None,
        'registration': None,
        'aircraft_model': None,
        'competition_number': None,
        'takeoff_timestamp': None,
        'takeoff_airfield': None,
        'landing_timestamp': None,
        'landing_airfield': None,
        'status': None,
        'launch_height': None,
        'launch_type': None,
        'average_launch_climb_rate': 0,
        'max_launch_climb_rate': 0,
        'launch_climb_rates': {},
        'launch_beacon_heights': [],
        'takeoff_detection_height': None,
        'launch_gradients': [],
        'launch_complete': False,
        'distance_to_nearest_airfield': None,
        'tug': None,
        'at_partner_registration': None,
        'last_latitude': None,
        'last_longitude': None,
        'last_altitude': None,
        'last_pings': [],
        'launch_rec_name': None,
        'aerotow_key': None
    }


def seconds_since_launch(flight_data):
    try:
        # log.warning(type(flight_data['timestamp']))
        # log.warning(type(flight_data['takeoff_timestamp']))

        return (flight_data['timestamp'] - flight_data['takeoff_timestamp']).total_seconds()
    except TypeError as err:
        log.warning(err)
        return None


def height_agl(flight_data):
    if flight_data['nearest_airfield']:
        return flight_data['altitude'] - flight_data['nearest_airfield']['elevation']


def launch_gradient(flight_data):
    # beacons don't always arrive in timestamp order
    try:
        last_launch_height = sorted(flight_data['launch_beacon_heights'])[-1]
    except TypeError:
        launch_beacon_heights = [tuple(sublist) for sublist in flight_data['launch_beacon_heights']]
        last_launch_height = sorted(launch_beacon_heights)[-1]
    if last_launch_height[0] == flight_data['takeoff_timestamp'].timestamp():
        return 0
    try:
        return (last_launch_height[1] - flight_data['takeoff_detection_height']) / (
                    datetime.fromtimestamp(last_launch_height[0]) - flight_data['takeoff_timestamp']).total_seconds()
    except TypeError:
        log.error('Bad gradient data: {}'.format(flight_data['registration']))
        log.error('({} - {})/({} - {})'.format(
            height_agl(flight_data),
            flight_data['takeoff_detection_height'],
            last_launch_height[0],
            flight_data['takeoff_timestamp']
        ))
        return False


def launch(flight_data, flight_repository, time_known=True):
    # if flight_data['status'] == 'ground':
    flight_data['status'] = 'air'
    flight_data['takeoff_airfield'] = flight_data['nearest_airfield']['id']
    flight_data['takeoff_timestamp'] = flight_data['timestamp']
    flight_data['takeoff_detection_height'] = height_agl(flight_data)
    # if time_known:
    # todo set a flag
    if flight_data['nearest_airfield']['launch_type_detection']:
        log.info('Yes to launch type detection')
        if flight_data['aircraft_type'] == 2:
            flight_data['launch_type'] = 'tug'
    else:
        if time_known:
            log.info('Launch type detection disabled for {} at {}'.format(flight_data['registration'],
                                                                          flight_data['nearest_airfield'][
                                                                              'nice_name']))
        else:
            log.info('Launch type detection unavailable for {} at {}'.format(flight_data['registration'],
                                                                             flight_data['nearest_airfield'][
                                                                                 'nice_name']))
        flight_data['launch_complete'] = True
        flight_data['launch_type'] = None
    # else:
    #     log.error("Can't launch an airborne aircraft!")


def set_launch_type(flight_data, flight_repository, launch_type):
    initial_launch_types = ['winch', 'aerotow_pair', 'aerotow_glider' 'self', 'tug', 'unknown, nearest field',
                            'aerotow_sl']
    updatable_launch_types = ['winch l/f']

    if flight_data['launch_type'] is None:
        if launch_type in initial_launch_types:
            flight_data['launch_type'] = launch_type
        else:
            log.error('{} not an initial launch type for {} at {} {}'.format(
                launch_type,
                flight_data['registration'] if flight_data['registration'] != 'UNKNOWN' else flight_data['address'],
                flight_data['nearest_airfield']['nice_name'],
                flight_data['timestamp']))

    elif flight_data['launch_type']:
        if launch_type in updatable_launch_types:
            flight_data['launch_type'] = launch_type
        else:
            log.error('Cannot change launch type for {} to non-failure type ({} from {}) during launch'.format(
                flight_data['registration'],
                launch_type,
                flight_data['launch_type']
            ))


def update(flight_data, flight_repository, beacon):
    flight_data['altitude'] = beacon['altitude']

    if flight_data['status'] == 'air' and not flight_data['launch_complete']:
        if not flight_data['takeoff_detection_height']:
            flight_data['launch_complete'] = True
        else:
            # update launch height if None or agl is greater
            height = height_agl(flight_data)
            if not flight_data['launch_height']:
                flight_data['launch_height'] = height
            elif height > flight_data['launch_height']:
                flight_data['launch_height'] = height

            unix_timestamp = flight_data['timestamp']
            unix_timestamp = unix_timestamp.timestamp()
            flight_data['launch_climb_rates'][unix_timestamp] = beacon['climb_rate']
            flight_data['launch_beacon_heights'].append((unix_timestamp, height_agl(flight_data)))
            gradient = launch_gradient(flight_data)
            flight_data['launch_gradients'].append(gradient)

    flight_data['ground_speed'] = beacon['ground_speed']
    flight_data['receiver_name'] = beacon['receiver_name']
    flight_data['timestamp'] = beacon['timestamp']
    flight_data['last_latitude'] = beacon['latitude']
    flight_data['last_longitude'] = beacon['longitude']
    flight_data['last_altitude'] = beacon['altitude']

    if flight_data['takeoff_timestamp'] and \
            not flight_data['launch_complete'] and \
            flight_data['launch_type'] not in ['aerotow_pair', 'aerotow_glider']:
        # todo: consider if last pings should be in aerotow object
        last_pings = deque(flight_data['last_pings'], maxlen=10)
        last_pings.append(
            {
                # 'timestamp': beacon['timestamp'],
                'altitude': beacon['altitude'],
                'latitude': beacon['latitude'],
                'longitude': beacon['longitude'],
                'receiver': beacon['receiver_name'],
                # 'signal': beacon['signal_quality']
            })
        if len(last_pings) == 10:
            # it's a deque ^
            flight_data['mean_recent_launch_altitude'] = mean([i['altitude'] for i in last_pings])
            flight_data['mean_recent_launch_latitude'] = mean([i['latitude'] for i in last_pings])
            flight_data['mean_recent_launch_longitude'] = mean([i['longitude'] for i in last_pings])

        flight_data['last_pings'] = list(last_pings)


def update_aerotow(flight_data, beacon, flight_repository, aerotow_repository):
    log.info('Updating aerotow for {}({})'.format(flight_data['address'], flight_data['registration']))
    if flight_data['aerotow_key']:
        aerotow_data = aerotow_repository.get_aerotow(flight_data['aerotow_key'])
        aerotow_processor.insert_aerotow_data(aerotow_data, flight_data, beacon, aerotow_repository, flight_repository)


def reset(flight_data, flight_repository):
    flight_data['takeoff_timestamp'] = None
    flight_data['takeoff_airfield'] = None
    flight_data['landing_timestamp'] = None
    flight_data['landing_airfield'] = None
    flight_data['launch_height'] = None
    flight_data['launch_type'] = None
    flight_data['average_launch_climb_rate'] = 0
    flight_data['max_launch_climb_rate'] = 0
    flight_data['launch_climb_rates'] = {}
    flight_data['launch_beacon_heights'] = []
    flight_data['takeoff_detection_height'] = None
    flight_data['launch_gradients'] = []
    flight_data['launch_complete'] = False
    flight_data['tug'] = None

    flight_data['last_latitude'] = None
    flight_data['last_longitude'] = None
    flight_data['last_altitude'] = None

    flight_data['last_pings'] = []
    flight_data['launch_rec_name'] = None

    flight_data['aerotow_key'] = None
    flight_data['at_partner_registration'] = None
