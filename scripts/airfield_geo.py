import requests
import json
import pprint
import time

CLUB_KEY_VALUES = ['clubid', 'title', 'address', 'geolat', 'geolong', 'civilian', 'service', 'uni', 'email', 'website', 'telephone', 'additional_voucher_information', 'link']

# key_values = []
# for key in club.keys():
#     if key not in key_values:
#         key_values.append(key)

#
# r = requests.get('https://www.gliding.co.uk/?clubfinder_mapmarkers=&returnurl=')
#
# json_response = r.json()
#
# with open('./airfield_data', 'w') as afd:
#     afd.write(json.dumps(json_response))


clubs = {}

def get_open_elevation(club):
    return requests.get(
        'https://api.open-elevation.com/api/v1/lookup?locations={},{}'.format(club['geolat'], club['geolong']))


with open('./airfield_data', 'r') as json_file:
    data = json.load(json_file)
    request_json = {'locations': []}
    for club in data['clubs']:

        club_post_json = {'latitude': float(club['geolat']), 'longitude': float(club['geolong'])}
        request_json['locations'].append(club_post_json)


    print(request_json)
    elevation_results = requests.post('https://api.open-elevation.com/api/v1/lookup',
                                      json=request_json,
                                      headers={'Content-Type': 'application/json'})
    print(elevation_results)
    print(elevation_results.text)
    pprint.pprint(elevation_results.json())
    print(elevation_results)
    json_results = elevation_results.json()

    with open('./raw_elevation_data.json', 'w') as raw_elevation:
        raw_elevation.write(json.dumps(json_results))

    for i, club in enumerate(data['clubs']):
        club_data = {
            'name': club['title'],
            'longitude': club['geolong'],
            'latitude': club['geolat'],
            'elevation': json_results['results'][i]['elevation']

        }
        club_key = club['title'].upper().replace(' ', '_')
        print(club_key + ' = ')
        pprint.pprint(club_data)
        clubs[club_key] = club_data


with open('./club_data.json', 'w') as club_data_file:
    club_data_file.write(json.dumps(club_data))

