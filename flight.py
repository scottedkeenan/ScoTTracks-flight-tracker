class Flight:
    def __init__(self, nearest_airfield, address, aircraft_type, altitude, ground_speed, receiver_name, timestamp,
                 registration, distance_to_nearest_airfield=None, tug=None):
        self.nearest_airfield = nearest_airfield
        self.address = address
        self.aircraft_type = aircraft_type
        self.altitude = altitude
        self.ground_speed = ground_speed
        self.receiver_name = receiver_name
        self.timestamp = timestamp # .strftime("%m/%d/%Y, %H:%M:%S")
        self.registration = registration

        self.takeoff_timestamp = None
        self.takeoff_airfield = None
        self.landing_timestamp = None
        self.landing_airfield = None
        self.status = None
        self.launch_height = None
        self.launch_type = None
        self.average_launch_climb_rate = 0
        self.max_launch_climb_rate = 0
        self.launch_climb_rates = []
        self.launch_complete = False
        self.distance_to_nearest_airfield = distance_to_nearest_airfield
        self.tug = tug

    def to_dict(self):
        return {
            'nearest_airfield': self.nearest_airfield,
            'address': self.address,
            'aircraft_type': self.aircraft_type,
            'altitude': self.altitude,
            'ground_speed': self.ground_speed,
            'receiver_name': self.receiver_name,
            'timestamp': self.timestamp,# .strftime("%m/%d/%Y, %H:%M:%S")
            'registration': self.registration,

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
            'tug': self.tug
        }

    def update(self, beacon):
        self.altitude = beacon['altitude']
        self.ground_speed = beacon['ground_speed']
        self.receiver_name = beacon['receiver_name']
        self.timestamp = beacon['timestamp']

    def launch(self):
        if self.status == 'ground':
            self.status = 'air'
            self.takeoff_airfield = self.nearest_airfield['name']
            self.takeoff_timestamp = self.timestamp
            if self.aircraft_type is 2:
                self.launch_type = 'tug'
        else:
            print("Can't launch an airborne aircraft!")

    def seconds_since_launch(self):
        try:
            return (self.timestamp - self.takeoff_timestamp).total_seconds()
        except TypeError:
            return None

    def set_launch_type(self, launch_type):
        initial_launch_types = ['winch', 'aerotow', 'self', 'tug']
        updatable_launch_types = ['winch l/f', 'tug']

        if self.launch_type is None:
            if launch_type in initial_launch_types:
                self.launch_type = launch_type
            else:
                print('Not an initial launch type')
        elif self.launch_type:
            if launch_type in updatable_launch_types:
                self.launch_type = updatable_launch_types
            else:
                print('Cannot change launch type to non-failure type during launch')


    def add_launch_climb_rate_point(self, climb_rate):
        self.launch_climb_rates.append(climb_rate)

    def agl(self):
        if self.nearest_airfield:
            return self.altitude - self.nearest_airfield['elevation']
