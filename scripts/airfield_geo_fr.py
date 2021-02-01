import requests
import json
import pprint
import xml.etree.ElementTree as ET
import re
from slugify import slugify, SLUG_OK


# DATA FROM:

airfield_json = []


with open('./datasources/france.json', 'r') as json_file:
    raw_data_json = json.load(json_file)['preload_data']['settings']['map']['locations']

for club in raw_data_json:
    anchor, para = club['content'].split('\n')
    element = ET.fromstring(anchor)
    club_name = element.attrib['title'].split(' –')[0]
    import unicodedata
    club_key = slugify(club_name, only_ascii=True)
    club_key = club_key.replace('’', '')

    airfield_json.append({
            'key': club_key,
            'name': club_name,
            'longitude': club['position']['lng'],
            'latitude': club['position']['lat'],
            'elevation': None,
            'country_code': 'FR',
            'is_active': True # assume true

        })

pprint.pprint(airfield_json)

# request_json = {'locations': []}
# for field in airfield_json:
#     club_post_json = {'latitude': float(field['latitude']), 'longitude': float(field['longitude'])}
#     request_json['locations'].append(club_post_json)
#
#
# print(request_json)
# elevation_results = requests.post('https://api.open-elevation.com/api/v1/lookup',
#                                   json=request_json,
#                                   headers={'Content-Type': 'application/json'})
#
# print(elevation_results)
# json_results = elevation_results.json()
# pprint.pprint(json_results)
#
# with open('./raw_elevation_data.json', 'w') as raw_elevation:
#     raw_elevation.write(json.dumps(json_results))

sql_lines = ["INSERT INTO `airfields` (`name`, `nice_name`, `latitude`, `longitude`, `elevation`, `country_code`, `is_active`) VALUES "]

print(sql_lines)

with open('./raw_elevation_data.json', 'r') as raw_elevation:
    raw_elevation_json = json.loads(raw_elevation.read())

for i, club in enumerate(airfield_json):

    sql_insert_string = "('{}', '{}', {}, {}, {}, '{}', {}),".format(
        club['key'],
        club['name'],
        club['latitude'],
        club['longitude'],
        raw_elevation_json['results'][i]['elevation'],
        club['country_code'],
        True
    )
    print(sql_insert_string)
    sql_lines.append(sql_insert_string)

sql_lines.append(';')

print(len(airfield_json), ' clubs')

with open('./fr_club_data.sql', 'w') as club_data_file:
    club_data_file.writelines(sql_lines)

