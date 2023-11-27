import pprint
from geopy import distance as measure_distance
import os
from statistics import mean
import logging
from collections import Counter

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


def new_aerotow(flight1, flight2):
    aerotow_data = {
        'aerotow_key': None,
        'flights': [
            flight1['address'],
            flight2['address']
        ],
        'check_failures': 0,
        'beacons': {},
        'flight_beacon_counts': {},
        'launch_rec_name': None
    }

    start_beacons = {int(flight1['takeoff_timestamp'].timestamp()): flight1,
                     int(flight2['takeoff_timestamp'].timestamp()): flight2}

    if len(start_beacons) == 2:
        earliest_time = min(list(start_beacons.keys()))
        latest_time = max(list(start_beacons.keys()))
        earliest_flight = start_beacons[earliest_time]
        latest_flight = start_beacons[latest_time]

        aerotow_data['beacons'][earliest_time] = {
            earliest_flight['address']: {
                'altitude': earliest_flight['last_altitude'],
                'latitude': earliest_flight['last_latitude'],
                'longitude': earliest_flight['last_longitude']
            }
        }

        count_forwards(aerotow_data, latest_time)

        aerotow_data['beacons'][latest_time] = {
            latest_flight['address']: {
                'altitude': latest_flight['last_altitude'],
                'latitude': latest_flight['last_latitude'],
                'longitude': latest_flight['last_longitude']
            }
        }
    else:
        earliest_time = min(list(start_beacons.keys()))

        aerotow_data['beacons'][earliest_time] = {
            flight1['address']: {
                'altitude': flight1['last_altitude'],
                'latitude': flight1['last_latitude'],
                'longitude': flight2['last_longitude']
            },
            flight2['address']: {
                'altitude': flight2['last_altitude'],
                'latitude': flight2['last_latitude'],
                'longitude': flight2['last_longitude']
            }
        }

    aerotow_data['check_counter_datetime'] = earliest_time

    aerotow_data['flight_beacon_counts'][flight1['address']] = 1
    aerotow_data['flight_beacon_counts'][flight2['address']] = 1

    log.debug('[A/T] Initial beacons: {}'.format(pprint.pformat(aerotow_data['beacons'])))
    return aerotow_data


def count_forwards(aerotow_data, target_timestamp):
    new_timestamp = list(aerotow_data['beacons'].keys())[-1]
    while new_timestamp <= target_timestamp:
        new_timestamp +=1
        aerotow_data['beacons'][new_timestamp] = {}


def abort(beacon_flight, aerotow_data, aerotow_repository, flight_repository):
    # logging.info('[A/T] failure beacons: {}'.format(pprint.pformat(aerotow_data['beacons'])))
    for address in [beacon_flight['address'], beacon_flight['tug']]:
        repository_flight = flight_repository.get_flight(address)
        repository_flight['launch_complete'] = True
        repository_flight['launch_height'] = None
        flight_repository.update_flight(repository_flight)
    beacon_flight['launch_complete'] = True
    beacon_flight['launch_height'] = None
    aerotow_repository.delete_aerotow(beacon_flight['aerotow_key'])


def insert_aerotow_data(aerotow_data, flight_data, beacon, aerotow_repository, flight_repository):
    # when an aircraft with an aerotow launch type gets a timestamp the dict is updated
    beacon_timestamp = int(beacon['timestamp'].timestamp())
    if aerotow_data['launch_rec_name'] and aerotow_data['launch_rec_name'] != beacon['receiver_name']:
        # exit early if there is a common rec name and this isn't from it
        log.debug("Skipping aerotow tracking: this beacon isn't from the common receiver")
        return
    if beacon_timestamp < list(aerotow_data['beacons'].keys())[0]:
        # exit early if this is from the past
        log.info("Skipping aerotow tracking: this beacon is from before the launch was detected")
        return

    if beacon_timestamp not in aerotow_data['beacons'].keys():
        # missing timestamps between the new one and the last in the dict are added
        count_forwards(aerotow_data, beacon_timestamp)
    try:
        # if the correct timestamp exists, just slot the data in
        aerotow_data['beacons'][beacon_timestamp][flight_data['address']] = {
            'altitude': beacon['altitude'],
            'latitude': beacon['latitude'],
            'longitude': beacon['longitude']
        }
    except KeyError:
        log.info('Timestamp {} missing from aerotow beacon keys'.format(beacon_timestamp))
        pass

    aerotow_data['flight_beacon_counts'][flight_data['address']] += 1

    check_complete(aerotow_data, beacon, flight_data, aerotow_repository, flight_repository)
    aerotow_repository.update_aerotow(aerotow_data)


def check_complete(aerotow_data, beacon, beacon_flight, aerotow_repository, flight_repository):
    # every 10 seconds check the average vertical/horizontal separation for the last 10 seconds
    # if they are outside parameters, mark the involved aircraft as launched, update the launch heights

    beacon_timestamp = int(beacon['timestamp'].timestamp())

    time_since_last_check = beacon_timestamp - aerotow_data['check_counter_datetime']
    log.debug('Seconds since check time: {}'.format(time_since_last_check))
    if time_since_last_check >= 10 and aerotow_data['check_failures'] < 5:
        log.info('Beacon counts for {}:{}'.format(aerotow_data['aerotow_key'], pprint.pformat(aerotow_data['flight_beacon_counts'])))
        # Not necessarily the tug but the aerotow partner
        tug_flight = flight_repository.get_flight(beacon_flight['tug'])
        if list(aerotow_data['flight_beacon_counts'].values())[0] > 10 and \
                list(aerotow_data['flight_beacon_counts'].values())[0] > 10:
            # set the pair to use only the most commonly seen beacon
            if not aerotow_data['launch_rec_name']:
                log.warning(pprint.pformat(beacon_flight))
                data = Counter([i['receiver'] for i in beacon_flight['last_pings']] + [i['receiver'] for i in tug_flight['last_pings']])
                log.warning(pprint.pformat(data))
                common_rec_name = (data.most_common(1)[0][0])
                log.info('Common receiver name for the aerotow pair {} is {}'.format(beacon_flight['aerotow_key'], common_rec_name))

                aerotow_data['launch_rec_name'] = common_rec_name
                aerotow_repository.update_aerotow(aerotow_data)
            # TODO: simplify this grouping of data
            last_positions = list(aerotow_data['beacons'].items())[-10:]

            grouped_metrics = {}

            for position_timestamp, position_data in last_positions:
                for aircraft_address in position_data:
                    if aircraft_address not in grouped_metrics.keys():
                        grouped_metrics[aircraft_address] = {
                            'altitude': [position_data[aircraft_address]['altitude']],
                            'latitude': [position_data[aircraft_address]['latitude']],
                            'longitude': [position_data[aircraft_address]['longitude']]
                        }
                    else:
                        grouped_metrics[aircraft_address]['altitude'].append(position_data[aircraft_address]['altitude'])
                        grouped_metrics[aircraft_address]['latitude'].append(position_data[aircraft_address]['latitude'])
                        grouped_metrics[aircraft_address]['longitude'].append(position_data[aircraft_address]['longitude'])

            log.debug('[A/T] Grouped metrics: {}'.format(pprint.pformat(grouped_metrics)))

            averages = {}
            for reg, data in grouped_metrics.items():
                averages[reg] = {
                    'altitude': mean(data['altitude']),
                    'latitude': mean(data['latitude']),
                    'longitude': mean(data['longitude'])
                }

            log.info('[A/T] Averages: {}'.format(pprint.pformat(averages)))

            average_addresses = list(averages.keys())
            log.info('average addresses: {}'.format(pprint.pformat(average_addresses)))

            if len(average_addresses) < 2:
                aerotow_data['check_failures'] += 1
                if aerotow_data['check_failures'] >= 5:
                    # todo: switch to climb rate based a/t tracking
                    abort(beacon_flight, aerotow_data, aerotow_repository, flight_repository)
                    log.info('Aborted aerotow tracking for {} ({}), too many failures'.format(beacon_flight['address'], aerotow_data['aerotow_key']))
                    return
                logging.info('Lost track of an aerotow aircraft, waiting another 10 seconds')
                aerotow_data['check_counter_datetime'] = beacon_timestamp
                log.info('Check counter datetime now {}'.format(aerotow_data['check_counter_datetime']))
                aerotow_repository.update_aerotow(aerotow_data)
                return
            else:
                aerotow_data['check_failures'] = 0

            vertical_separation = averages[average_addresses[0]]['altitude'] - averages[average_addresses[1]]['altitude']
            horizontal_separation = measure_distance.distance(
                (averages[average_addresses[0]]['latitude'],
                 averages[average_addresses[0]]['longitude']),
                (averages[average_addresses[1]]['latitude'],
                 averages[average_addresses[1]]['longitude'])
            ).meters

            # Check vertical separation with tug/other in pair
            if vertical_separation > 50 or vertical_separation < -50:
                log.info(
                    'Aerotow involving {} and {} is complete at {} with a vertical separation of {} at a height of {} ({} ft)'.format(
                        beacon_flight['address'] if beacon_flight['registration'] == 'UNKNOWN' else beacon_flight['registration'],
                        tug_flight['address'] if tug_flight['registration'] == 'UNKNOWN' else tug_flight['registration'],
                        beacon_flight['takeoff_airfield'],
                        vertical_separation,
                        beacon_flight['launch_height'],
                        beacon_flight['launch_height'] * 3.281
                    ))
                log.info('Horizontal separation was: {}'.format(horizontal_separation))
                beacon_flight['launch_complete'] = True
                flight_repository.update_flight(beacon_flight)
                tug_flight['launch_complete'] = True
                flight_repository.update_flight(tug_flight)
                aerotow_repository.update_aerotow(aerotow_data)
                return

            if horizontal_separation > 300:
                log.info(
                    'Aerotow involving {} and {} is complete at {} with a horizontal separation of {} at a height of {} ({} ft)'.format(
                        beacon_flight['address'] if beacon_flight['registration'] == 'UNKNOWN' else beacon_flight['registration'],
                        tug_flight['address'] if tug_flight['registration'] == 'UNKNOWN' else tug_flight['registration'],
                        beacon_flight['takeoff_airfield'],
                        horizontal_separation,
                        beacon_flight['launch_height'],
                        beacon_flight['launch_height'] * 3.281
                    ))
                log.info('Vertical separation was: {}'.format(vertical_separation))
                beacon_flight['launch_complete'] = True
                flight_repository.update_flight(beacon_flight)
                tug_flight['launch_complete'] = True
                flight_repository.update_flight(tug_flight)
                aerotow_repository.update_aerotow(aerotow_data)
                return
            aerotow_data['check_counter_datetime'] = beacon_timestamp
            log.debug('Check counter datetime now {}'.format(aerotow_data['check_counter_datetime']))

# work out which is in front (tug)
# update the aircraft with their types


# flight1 = Flight(
#     None,
#     'DF115D',
#     '1',
#     '100',
#     '60',
#     'Scott',
#     datetime.datetime(2020, 5, 17, 2, 22, 3 ),
#     'G-BSTR'
# )
#
# flight1.takeoff_timestamp = datetime.datetime(2020, 5, 17, 2, 22, 3 )
# flight1.last_latitude = 1
# flight1.last_longitude = 2
# flight1.last_altitude = 3
#
# flight2 = Flight(
#     None,
#     'XXXXXX',
#     '12',
#     '132',
#     '61',
#     'Lesley',
#     datetime.datetime(2020, 5, 17, 2, 22, 0 ),
#     'G-CNUT'
# )
#
# flight2.takeoff_timestamp = datetime.datetime(2020, 5, 17, 2, 22, 0 )
# flight2.last_latitude = 1
# flight2.last_longitude = 2
# flight2.last_altitude = 3
#
# at = Aerotow(flight1, flight2)


# log.info('=' * 10)
# for i in range(10):
#     log.info(i)
#     log.info('Time. {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['timestamp'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['timestamp']))
#     log.info('Alt.  {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['altitude'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['altitude']))
#     log.info('lat.  {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['latitude'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['latitude']))
#     log.info('long. {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['longitude'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['longitude']))
#     log.info('rec.  {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['receiver'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['receiver']))
#     log.info('qual. {}: {} | {}: {}'.format(flight.registration, flight.last_pings[i]['signal'],
#                                             flight.tug.registration, flight.tug.last_pings[i]['signal']))
#     vertical_separation = flight.last_pings[i]['altitude'] - flight.tug.last_pings[i]['altitude']
#     log.info('Vertical: {}'.format(vertical_separation))
#     horizontal_separation = measure_distance.distance(
#         (flight.last_pings[i]['latitude'],
#          flight.last_pings[i]['longitude']),
#         (flight.tug.last_pings[i]['latitude'],
#          flight.tug.last_pings[i]['longitude'])).meters
#     log.info('Horizontal: {}'.format(horizontal_separation))
#     log.info('=' * 10)
