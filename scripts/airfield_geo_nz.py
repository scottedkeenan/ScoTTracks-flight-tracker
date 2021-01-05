import requests
import json
import pprint
import xml.etree.ElementTree as ET


# data from: http://gliding.co.nz/clubs/map/

tree = ET.parse('doc.kml')
root = tree.getroot()

airfield_json = []

for child in root.iter('Placemark'):
    club_name = child.find('name').text.strip()
    club_key = club_name.upper().replace(' ', '_')
    coords = child.find('Point').find('coordinates').text.strip().split(',')
    airfield_json.append({
            'key': club_key,
            'name': club_name,
            'longitude': coords[0],
            'latitude': coords[1],
            'elevation': None,
            'country': 'NZ',
            'is_active': True # assume true

        })

    # if child.tag == 'Placemark':
    #     for tag in child:
    #         print(tag.tag, tag.text)

pprint.pprint(airfield_json)




request_json = {'locations': []}
for field in airfield_json:
    club_post_json = {'latitude': float(field['latitude']), 'longitude': float(field['longitude'])}
    request_json['locations'].append(club_post_json)


print(request_json)
elevation_results = requests.post('https://api.open-elevation.com/api/v1/lookup',
                                  json=request_json,
                                  headers={'Content-Type': 'application/json'})

json_results = elevation_results.json()
pprint.pprint(json_results)

with open('./raw_elevation_data.json', 'w') as raw_elevation:
    raw_elevation.write(json.dumps(json_results))

sql_lines = ["INSERT INTO `airfields` (`name`, `nice_name`, `latitude`, `longitude`, `elevation`, `country`, `is_active`) VALUES "]

print(sql_lines)
with open('./raw_elevation_data.json', 'r') as raw_elevation:
    raw_elevation_json = json.loads(raw_elevation.read())

for i, club in enumerate(airfield_json):

    sql_insert_string = "('{}', '{}', {}, {}, {}, {}, {}),".format(
        club['key'],
        club['name'],
        club['latitude'],
        club['longitude'],
        raw_elevation_json['results'][i]['elevation'],
        "'NZ'",
        True
    )
    print(sql_insert_string)
    sql_lines.append(sql_insert_string)


    # club_data = {
    #     'name': club['ClubName'],
    #     'longitude': club['Lng'],
    #     'latitude': club['Lat'],
    #     'elevation': json_results['results'][i]['elevation'],
    #     'country': 'AU',
    #     'is_active': True if club['State'] == 'Active' else False
    #
    # }
    # club_key = club['ClubName'].upper().replace(' ', '_')
    # print(club_key + ' = ')
    # pprint.pprint(club_data)
    # clubs[club_key] = club_data
sql_lines.append(';')

print(len(airfield_json), ' clubs')

with open('./nz_club_data.sql', 'a') as club_data_file:
    club_data_file.writelines(sql_lines)

