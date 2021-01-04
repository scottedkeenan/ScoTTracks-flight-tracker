class Aircraft:
    def __init__(self, airfield_name, address, address_type, altitude, ground_speed, receiver_name, reference_timestamp, registration):
        self.airfield = airfield_name
        self.address = address
        self.address_type = address_type
        self.altitude = altitude
        self.ground_speed = ground_speed
        self.receiver_name = receiver_name
        self.reference_timestamp = reference_timestamp # .strftime("%m/%d/%Y, %H:%M:%S")
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

    def to_dict(self):
        return {
            'airfield': self.airfield,
            'address': self.address,
            'address_type': self.address_type,
            'altitude': self.altitude,
            'ground_speed': self.ground_speed,
            'receiver_name': self.receiver_name,
            'reference_timestamp': self.reference_timestamp,# .strftime("%m/%d/%Y, %H:%M:%S")
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
            'launch_complete': self.launch_complete
        }

    def add_launch_climb_rate_point(self, climb_rate):
        self.launch_climb_rates.append(climb_rate)
