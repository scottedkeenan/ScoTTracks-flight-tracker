import requests
import json
import pprint
from slugify import slugify, SLUG_OK

# data from https://gfa.azolve.com/clubfinder.htm

def get_open_elevation(club):
    return requests.get(
        'https://api.open-elevation.com/api/v1/lookup?locations={},{}'.format(club['geolat'], club['geolong']))


with open('./datasources/aus.json', 'r') as json_file:
    clubs = {}
    data = json.load(json_file)
    request_json = {'locations': []}
    for club in data[0]['Result']:
        club_post_json = {'latitude': float(club['Lat']), 'longitude': float(club['Lng'])}
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

    sql_lines = ["INSERT INTO `airfields` (`name`, `nice_name`, `latitude`, `longitude`, `elevation`, `country_code`, `is_active`) VALUES "]

    print(sql_lines)
    # with open('./raw_elevation_data.json', 'r') as raw_elevation:
    #     raw_elevation_json = json.loads(raw_elevation.read())

    for i, club in enumerate(data[0]["Result"]):

        sql_insert_string = "('{}', '{}', {}, {}, {}, {}, {}),".format(
            slugify(club['ClubName'], only_ascii=True),
            club['ClubName'],
            club['Lat'],
            club['Lng'],
            json_results['results'][i]['elevation'],
            "'AU'",
            True if club['State'] == 'Active' else False
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

    print(len(data[0]["Result"]), ' clubs')

    with open('./au_club_data.sql', 'w') as club_data_file:
        club_data_file.writelines(sql_lines)

