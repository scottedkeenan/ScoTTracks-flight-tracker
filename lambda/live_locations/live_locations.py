import os
from datetime import datetime, timedelta

from repository.redis.flight_repository_redis import FlightRepositoryRedis
# import logging

# log = logging.getLogger(__name__)
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format='%(asctime)s [%(levelname)s] - %(message)s')

flight_repo = FlightRepositoryRedis(
    {'TRACKER': {'redis_host': os.environ['redis_host'], 'redis_port': os.environ['redis_port']}})


def lambda_handler(event, context):
    aircraft = flight_repo.get_all_flights()
    aircraft_feature_collection = []
    for k, v in aircraft.items():
        # Filter unseen
        if datetime.now() > v['timestamp'] + timedelta(minutes=int(os.environ['unseen_after_time'])):
            continue
        # Filter None pos
        if v['last_longitude'] is None or v['last_latitude'] is None:
            continue
        aircraft_feature_collection.append(
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [v['last_longitude'], v['last_latitude']]
                },
                'properties': {
                    'id': k if v['registration'] == 'UNKNOWN' else v['registration'],
                    'status': v['status']
                }
            })

    geojson_data = {
        'type': 'FeatureCollection',
        'features': aircraft_feature_collection
    }

    return geojson_data
