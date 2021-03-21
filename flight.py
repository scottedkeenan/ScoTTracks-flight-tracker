from collections import deque
from statistics import mean
import os

import logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

class Flight:
    def __init__(self, nearest_airfield, address, aircraft_type, altitude, ground_speed, receiver_name, timestamp,
                 registration, aircraft_model, competition_number, distance_to_nearest_airfield=None, tug=None):
        self.nearest_airfield = nearest_airfield
        self.address = address
        self.aircraft_type = aircraft_type
        self.altitude = altitude
        self.ground_speed = ground_speed
        self.receiver_name = receiver_name
        self.timestamp = timestamp # .strftime("%m/%d/%Y, %H:%M:%S")
        self.registration = registration
        self.aircraft_model = aircraft_model
        self.competition_number = competition_number

        self.takeoff_timestamp = None
        self.takeoff_airfield = None
        self.landing_timestamp = None
        self.landing_airfield = None
        self.status = None
        self.launch_height = None
        self.launch_type = None
        self.average_launch_climb_rate = 0
        self.max_launch_climb_rate = 0
        self.launch_climb_rates = {}
        self.launch_beacon_heights = []
        self.takeoff_detection_height = None
        self.launch_gradients = []
        self.launch_complete = False
        self.distance_to_nearest_airfield = distance_to_nearest_airfield
        self.tug = tug

        self.last_latitude = None
        self.last_longitude = None
        self.last_altitude = None

        self.last_pings = deque([], maxlen=10)
        self.launch_rec_name = None

        self.aerotow = None

    def to_dict(self):

        try:
            if self.tug:
                tug_registration = self.tug.registration if self.tug.registration != 'UNKNOWN' else self.tug.address
            else:
                tug_registration = None
        except AttributeError:
            tug_registration = self.tug

        return {
            'nearest_airfield': self.nearest_airfield,
            'address': self.address,
            'aircraft_type': self.aircraft_type,
            'altitude': self.altitude,
            'ground_speed': self.ground_speed,
            'receiver_name': self.receiver_name,
            'timestamp': self.timestamp,# .strftime("%m/%d/%Y, %H:%M:%S")
            'registration': self.registration,
            'aircraft_model': self.aircraft_model,
            'competition_number': self.competition_number,

            'takeoff_timestamp': self.takeoff_timestamp,
            'takeoff_airfield': self.takeoff_airfield,
            'landing_timestamp': self.landing_timestamp,
            'landing_airfield': self.landing_airfield,
            'status': self.status,
            'launch_height': self.launch_height,
            'launch_type': self.launch_type,
            'average_launch_climb_rate': self.average_launch_climb_rate,
            'max_launch_climb_rate': self.max_launch_climb_rate,
            'launch_climb_rates': self.launch_climb_rates,
            'launch_complete': self.launch_complete,
            'distance_to_nearest_airfield': self.distance_to_nearest_airfield,
            'tug': tug_registration

        }

    def update(self, beacon):
        self.altitude = beacon['altitude']

        if self.status == 'air' and not self.launch_complete:
            if not self.takeoff_detection_height:
                self.launch_complete = True
            else:
                # update launch height if None or agl is greater
                agl = self.agl()
                if not self.launch_height:
                    self.launch_height = agl
                elif agl > self.launch_height:
                    self.launch_height = agl

                self.launch_climb_rates[self.timestamp] = beacon['climb_rate']
                self.launch_beacon_heights.append((self.timestamp, self.agl()))
                launch_gradient = self.launch_gradient()
                self.launch_gradients.append(launch_gradient)

        self.ground_speed = beacon['ground_speed']
        self.receiver_name = beacon['receiver_name']
        self.timestamp = beacon['timestamp']
        self.last_latitude = beacon['latitude']
        self.last_longitude = beacon['longitude']
        self.last_altitude = beacon['altitude']

        if self.takeoff_timestamp and self.launch_type not in ['aerotow_pair', 'aerotow_glider'] and not self.launch_complete:
            # todo: consider if last pings should be in aerotow object
            self.last_pings.append(
                {
                    'timestamp': beacon['timestamp'],
                    'altitude': beacon['altitude'],
                    'latitude': beacon['latitude'],
                    'longitude': beacon['longitude'],
                    'receiver': beacon['receiver_name'],
                    'signal': beacon['signal_quality']
                })
            if len(self.last_pings) == 10:
                # it's a deque ^
                self.mean_recent_launch_altitude = mean([i['altitude'] for i in self.last_pings])
                self.mean_recent_launch_latitude = mean([i['latitude'] for i in self.last_pings])
                self.mean_recent_launch_longitude = mean([i['longitude'] for i in self.last_pings])

    def launch(self, time_known=True):
        if self.status == 'ground':
            self.status = 'air'
            self.takeoff_airfield = self.nearest_airfield['id']
            self.takeoff_timestamp = self.timestamp
            self.takeoff_detection_height = self.agl()
            # if time_known:
                # todo set a flag
            if self.nearest_airfield['launch_type_detection']:
                log.info('Yes to launch type detection')
                if self.aircraft_type == 2:
                    self.launch_type = 'tug'
            else:
                if time_known:
                    log.info('Launch type detection disabled for {} at {}'.format(self.registration,
                                                                                  self.nearest_airfield['nice_name']))
                else:
                    log.info('Launch type detection unavailable for {} at {}'.format(self.registration,
                                                                                  self.nearest_airfield['nice_name']))
                self.launch_complete = True
                self.launch_type = None
        else:
            log.error("Can't launch an airborne aircraft!")

    def seconds_since_launch(self):
        try:
            return (self.timestamp - self.takeoff_timestamp).total_seconds()
        except TypeError:
            return None

    def launch_gradient(self):
        # beacons don't aways arrive in timestamp order

        last_launch_height = sorted(self.launch_beacon_heights)[-1]
        if last_launch_height[0] == self.takeoff_timestamp:
            return 0
        try:
            return (last_launch_height[1] - self.takeoff_detection_height) / (last_launch_height[0] - self.takeoff_timestamp).total_seconds()
        except TypeError:
            log.error('Bad gradient data: {}'.format(self.registration))
            log.error('({} - {})/({} - {})'.format(
                self.agl(),
                self.takeoff_detection_height,
                last_launch_height[0],
                self.takeoff_timestamp
            ))
            return False

    def set_launch_type(self, launch_type):
        initial_launch_types = ['winch', 'aerotow_pair', 'aerotow_glider' 'self', 'tug', 'unknown, nearest field', 'aerotow_sl']
        updatable_launch_types = ['winch l/f']

        if self.launch_type is None:
            if launch_type in initial_launch_types:
                self.launch_type = launch_type
            else:
                log.error('{} not an initial launch type for {} at {} {}'.format(
                    launch_type,
                    self.registration if self.registration != 'UNKNOWN' else self.address,
                    self.nearest_airfield['nice_name'],
                    self.timestamp))
        elif self.launch_type:
            if launch_type in updatable_launch_types:
                self.launch_type = updatable_launch_types
            else:
                log.error('Cannot change launch type to non-failure type during launch')

    def agl(self):
        if self.nearest_airfield:
            return self.altitude - self.nearest_airfield['elevation']

    def recent_launch_averages(self):
        if self.mean_recent_launch_altitude and self.mean_recent_launch_latitude and self.mean_recent_launch_longitude:
            return {
                'altitude': self.mean_recent_launch_altitude,
                'latitude': self.mean_recent_launch_latitude,
                'longitude': self.mean_recent_launch_longitude
            }
        else:
            return None

    def update_aerotow(self, beacon):
        if self.aerotow:
            self.aerotow.insert_data(self, beacon)
