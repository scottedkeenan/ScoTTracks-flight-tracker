from collections import deque
from datetime import datetime
from statistics import mean
import os

import logging
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
        'at-partner': None,
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
    last_launch_height = sorted(flight_data['launch_beacon_heights'])[-1]
    if last_launch_height[0] == flight_data['takeoff_timestamp']:
        return 0
    try:
        return (last_launch_height[1] - flight_data['takeoff_detection_height']) / (
                    last_launch_height[0] - flight_data['takeoff_timestamp']).total_seconds()
    except TypeError:
        log.error('Bad gradient data: {}'.format(flight_data['registration']))
        log.error('({} - {})/({} - {})'.format(
            height_agl(flight_data),
            flight_data['takeoff_detection_height'],
            last_launch_height[0],
            flight_data['takeoff_timestamp']
        ))
        return False


def launch(flight_data, time_known=True):
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


def set_launch_type(flight_data, launch_type):
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

def update(flight_data, beacon):
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

            flight_data['launch_climb_rates'][flight_data['timestamp']] = beacon['climb_rate']
            flight_data['launch_beacon_heights'].append((flight_data['timestamp'], height_agl(flight_data)))
            gradient = launch_gradient(flight_data)
            flight_data['launch_gradients'].append(gradient)

    flight_data['ground_speed'] = beacon['ground_speed']
    flight_data['receiver_name'] = beacon['receiver_name']
    flight_data['timestamp'] = beacon['timestamp']
    flight_data['last_latitude'] = beacon['latitude']
    flight_data['last_longitude'] = beacon['longitude']
    flight_data['last_altitude'] = beacon['altitude']

    if flight_data['takeoff_timestamp'] and \
            flight_data['launch_type'] not in ['aerotow_pair', 'aerotow_glider'] and \
            not flight_data['launch_complete']:
        # todo: consider if last pings should be in aerotow object
        last_pings = deque(flight_data['last_pings'], maxlen=10)
        last_pings.append(
            {
                'timestamp': beacon['timestamp'],
                'altitude': beacon['altitude'],
                'latitude': beacon['latitude'],
                'longitude': beacon['longitude'],
                'receiver': beacon['receiver_name'],
                'signal': beacon['signal_quality']
            })
        if len(last_pings) == 10:
            # it's a deque ^
            flight_data['mean_recent_launch_altitude'] = mean([i['altitude'] for i in last_pings])
            flight_data['mean_recent_launch_latitude'] = mean([i['latitude'] for i in last_pings])
            flight_data['mean_recent_launch_longitude'] = mean([i['longitude'] for i in last_pings])

        flight_data['last_pings'] = list(last_pings)


def update_aerotow(flight_data, aerotow_repository, beacon):
    if flight_data['aerotow_key']:
        aerotow_repository.get_aerotow(flight_data['aerotow_key']).insert_data(flight_data, beacon)


def reset(flight_data):
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


# class FlightProcessor:

    # def to_dict(self):
    #
    #     try:
    #         if self.tug:
    #             tug_registration = self.tug.registration if self.tug.registration != 'UNKNOWN' else self.tug.address
    #         else:
    #             tug_registration = None
    #     except AttributeError:
    #         tug_registration = self.tug
    #
    #     return {
    #         'nearest_airfield': self.nearest_airfield,
    #         'address': self.address,
    #         'aircraft_type': self.aircraft_type,
    #         'altitude': self.altitude,
    #         'ground_speed': self.ground_speed,
    #         'receiver_name': self.receiver_name,
    #         'timestamp': self.timestamp,# .strftime("%m/%d/%Y, %H:%M:%S")
    #         'registration': self.registration,
    #         'aircraft_model': self.aircraft_model,
    #         'competition_number': self.competition_number,
    #
    #         'takeoff_timestamp': self.takeoff_timestamp,
    #         'takeoff_airfield': self.takeoff_airfield,
    #         'landing_timestamp': self.landing_timestamp,
    #         'landing_airfield': self.landing_airfield,
    #         'status': self.status,
    #         'launch_height': self.launch_height,
    #         'launch_type': self.launch_type,
    #         'average_launch_climb_rate': self.average_launch_climb_rate,
    #         'max_launch_climb_rate': self.max_launch_climb_rate,
    #         'launch_climb_rates': self.launch_climb_rates,
    #         'launch_complete': self.launch_complete,
    #         'distance_to_nearest_airfield': self.distance_to_nearest_airfield,
    #         'tug': tug_registration
    #
    #     }


    # def recent_launch_averages(self):
    #     if self.mean_recent_launch_altitude and self.mean_recent_launch_latitude and self.mean_recent_launch_longitude:
    #         return {
    #             'altitude': self.mean_recent_launch_altitude,
    #             'latitude': self.mean_recent_launch_latitude,
    #             'longitude': self.mean_recent_launch_longitude
    #         }
    #     else:
    #         return None