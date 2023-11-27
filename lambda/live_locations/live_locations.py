import os
from datetime import datetime, timedelta

from repository.redis.flight_repository_redis import FlightRepositoryRedis
# import logging

# log = logging.getLogger(__name__)
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format='%(asctime)s [%(levelname)s] - %(message)s')

flight_repo = FlightRepositoryRedis(
    {'TRACKER': {'redis_host': os.environ['redis_host'], 'redis_port': os.environ['redis_port']}})


def lambda_handler(event, context):
    aircraft = flight_repo.get_aircraft_in_radius(0,0,12742)
    aircraft_feature_collection = []
    for f in aircraft:
        # Filter unseen
        if datetime.now() > f['aircraft']['timestamp'] + timedelta(minutes=int(os.environ['unseen_after_time'])):
            continue
        # Filter None pos
        if f['aircraft']['last_longitude'] is None or f['aircraft']['last_latitude'] is None:
            continue
        aircraft_feature_collection.append(
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [f['aircraft']['last_longitude'], f['aircraft']['last_latitude']]
                },
                'properties': {
                    'id': f['aircraft']['address'] if f['aircraft']['registration'] == 'UNKNOWN' else f['aircraft']['registration'],
                    'status': f['aircraft']['status']
                }
            })

    geojson_data = {
        'type': 'FeatureCollection',
        'features': aircraft_feature_collection
    }

    return geojson_data
