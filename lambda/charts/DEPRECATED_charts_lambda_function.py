# DEPRECATED

import json
import tempfile

import boto3
import folium
import pandas as pd

def average_coords(coord_list):
    """
    Calculates the average x and y value of a list of coordinates and returns a tuple
    of average x, average y.
    """
    one = []
    two = []
    for pair in coord_list:
        one.append(pair[0])
        two.append(pair[1])
    return (sum(one) / len(one)), (sum(two) / len(two))


def generate_map_with_route(location_list, color='red'):
    """
    Generates a map with the route polyline rendered in the given colour
    """
    route_feature_group = folium.FeatureGroup(name='Route')
    route_feature_group.add_child(folium.vector_layers.PolyLine(locations=location_list, color=color))
    endpoints_feature_group = folium.FeatureGroup(name='Endpoints')
    endpoints_feature_group.add_child(folium.Marker(location=location_list[0], popup='Start'))
    endpoints_feature_group.add_child(folium.Marker(location=location_list[len(location_list) - 1], popup='Finish'))
    # todo: Calculate zoom start

    df = pd.DataFrame(location_list, columns=['Lat', 'Long'])

    sw = df[['Lat', 'Long']].min().values.tolist()
    ne = df[['Lat', 'Long']].max().values.tolist()

    map = folium.Map(
        location=average_coords(location_list),
        zoom_start=15
    )
    map.add_child(route_feature_group)
    map.add_child(endpoints_feature_group)
    map.fit_bounds([sw, ne])

    folium.TileLayer(
        tiles='https://api.tiles.openaip.net/api/data/openaip/{z}/{x}/{y}.png' + '?apiKey={}'.format(API_KEY),
        attr='Airspace: <a href="https://www.openaip.net">Open AIP<a>'
    ).add_to(map)

    return map

def lambda_handler(event, context):
    print(event)
    # event = json.loads(event['body'])
    s3_key = event['Records'][0]['s3']['object']['key']
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    print(s3_key)
    s3_client = boto3.client('s3')
    
    tempdir = tempfile.gettempdir()
    print(tempdir)
    
    with open('{}/{}'.format(tempdir, s3_key), 'wb') as f:
        s3_client.download_fileobj(bucket_name, s3_key, f)
    
    with open('/tmp/{}'.format(s3_key), 'r') as f:
        event = json.loads(f.read())
 
        if event['data']:
            coords = []

            for row in event['data']:
                coords.append([float(row['latitude']), float(row['longitude'])])
            # for point in coords:
            #     print(point)

            print(len(coords))
            generate_map_with_route(coords).save('/tmp/map.html')

            # Upload the file
            s3_client = boto3.client('s3')
            response = s3_client.upload_file(
                '/tmp/map.html',
                'scotttracks-graphs',
                'maps/{}-{}.html'.format(
                    event['address'],
                    event['start_time']),
                ExtraArgs={'ContentType': 'text/html'}
                )
        else:
            return {
            'statusCode': 200,
            'body': json.dumps('No data found')
        }

        
