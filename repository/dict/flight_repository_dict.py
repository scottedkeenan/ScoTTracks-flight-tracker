class FlightRepositoryDict:
    def __init__(self):
        self.flight_dict = {}

    def add_flight(self, address, flight_json):
        self.flight_dict[address] = flight_json

    def get_flight(self, address):
        return self.flight_dict[address]

    def get_all_flights(self):
        return self.flight_dict

    def get_all_addresses(self):
        return self.flight_dict.keys()

    def update_flight(self, flight_json, address=None):
        if address:
            self.flight_dict[address] = flight_json
        else:
            self.flight_dict[flight_json['address']] = flight_json

    def delete_flight(self, address):
        self.flight_dict[address].pop()
