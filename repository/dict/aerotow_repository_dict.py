def build_aerotow_key(aerotow):
    flight_addresses = sorted(aerotow['flights'])
    return '_'.join(flight_addresses)


class AerotowRepositoryDict:
    def __init__(self):
        self.aerotow_dict = {}

    def add_aerotow(self, aerotow_json):
        key = build_aerotow_key(aerotow_json)
        aerotow_json['aerotow_key'] = key
        self.aerotow_dict[key] = aerotow_json
        return key

    def get_aerotow(self, key):
        return self.aerotow_dict[key]

    def get_all_aerotows(self):
        return self.aerotow_dict

    def get_all_addresses(self):
        return self.aerotow_dict.keys()

    def update_aerotow(self, aerotow_json, key=None):
        if not key:
            key = aerotow_json['aerotow_key']
        self.aerotow_dict[key] = aerotow_json

    def delete_aerotow(self, key):
        self.aerotow_dict.pop(key)

    def key_exists(self, key):
        return True if 'flight_tracker_aerotow' + key in self.aerotow_dict.keys() else False
