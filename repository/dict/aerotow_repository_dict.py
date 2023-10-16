def build_aerotow_key(aerotow):
    flight_addresses = sorted(aerotow.flights.keys())
    return '_'.join(flight_addresses)


class AerotowRepositoryDict:
    def __init__(self):
        self.aerotow_dict = {}

    def add_aerotow(self, aerotow_json):
        key = build_aerotow_key(aerotow_json)
        self.aerotow_dict[key] = aerotow_json
        return key

    def get_aerotow(self, key):
        return self.aerotow_dict[key]

    def get_all_aerotows(self):
        return self.aerotow_dict

    def get_all_addresses(self):
        return self.aerotow_dict.keys()

    def update_aerotow(self, key, aerotow_json):
        self.aerotow_dict[key] = aerotow_json

    def delete_aerotow(self, key):
        self.aerotow_dict[key].pop()
