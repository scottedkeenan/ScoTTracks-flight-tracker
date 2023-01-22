import json
import os

import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.dates as mdates

import boto3
import folium
import pandas as pd

AIP_API_KEY = os.environ['AIP_API_KEY']


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


def generate_height_speed_graph(graph_data, filepath):
    time_num = matplotlib.dates.datestr2num(graph_data['times'])

    ax = plt.gca()

    myFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(myFmt)

    locator = mdates.DayLocator()
    ax.xaxis.set_major_locator(locator)

    plt.plot_date(time_num, graph_data['y1'], linestyle='-', linewidth=1.0, label='Altitude', marker='.', ms=3, mec='r', mfc='r')
    plt.plot_date(time_num, graph_data['y2'], linestyle='-', linewidth=1.0, label='Ground Speed', marker='.', ms=3, mec='r', mfc='r')
    plt.xlabel('time')
    plt.ylabel('Altitude in m / speed in kph')
    # plt.title('Interesting Graph\nCheck it out')
    plt.legend()
    plt.grid(True)
    plt.savefig(filepath)

    plt.clf()
    plt.cla()
    plt.close()


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
        tiles='https://api.tiles.openaip.net/api/data/openaip/{z}/{x}/{y}.png' + '?apiKey={}'.format(AIP_API_KEY),
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
    
    import tempfile
    tempdir = tempfile.gettempdir()
    print(tempdir)
    
    with open('{}/{}'.format(tempdir, s3_key), 'wb') as f:
        s3_client.download_fileobj(bucket_name, s3_key, f)
    
    with open('/tmp/{}'.format(s3_key), 'r') as f:
        event = json.loads(f.read())
 
        if event['data']:
            times = []
            y1 = []
            y2 = []

            for row in event['data']:
                times.append((row[0]))
                y1.append((float(row[1])))
                y2.append((float(row[2])))

            graph_data = {
                'times': times,
                'y1': y1,
                'y2': y2
            }

            graph_filepath = '{}/{}-{}.png'.format(
                '/tmp',
                event['address'],
                event['start_time']
            )

            generate_height_speed_graph(graph_data, graph_filepath)

            # Upload the file
            s3_client = boto3.client('s3')
            response = s3_client.upload_file(
                '{}/{}-{}.png'.format(
                    '/tmp',
                    event['address'],
                    event['start_time']),
                'scotttracks-graphs',
                'graphs/{}-{}.png'.format(
                    event['address'],
                    event['start_time']),
                ExtraArgs={'ContentType': 'image/png'}
                )

            print('Graph response: {}'.format(response))

            # prepare map data
            coords = []
            for row in event['data']:
                coords.append([float(row[4]), float(row[5])])

            map_filepath = '{}/{}-{}.html'.format(
                '/tmp',
                event['address'],
                event['start_time']
            )

            generate_map_with_route(coords).save(map_filepath)

            # Upload the file
            s3_client = boto3.client('s3')
            response = s3_client.upload_file(
                '{}/{}-{}.html'.format(
                    '/tmp',
                    event['address'],
                    event['start_time']),
                'scotttracks-graphs',
                'maps/{}-{}.html'.format(
                    event['address'],
                    event['start_time']),
                ExtraArgs={'ContentType': 'text/html'}
                )

            print('Map response: {}'.format(response))

        else:
            return {
            'statusCode': 200,
            'body': json.dumps('No data found')
        }

        
