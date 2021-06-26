import datetime
import pprint
from geopy import distance as measure_distance
import os
import logging

from statistics import mean
from collections import Counter

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class Aerotow:
    def __init__(self, flight1, flight2):
        log.info('Creating new AT object')

        self.flights = {
            flight1.address: flight1,
            flight2.address:  flight2
        }

        # log.info('[A/T] flights: {}'.format(pprint.pformat(self.flights)))

        self.check_failures = 0


        # start a dict with timestamps as key, 1 every second
        # values are dict of {g-cgcu: {alt:1, lat:1, lon:1, g-cief :{...}}
        self._beacons = {}
        # get earliest takeoff timestamp for the pair
        self._start_beacons = {flight1.takeoff_timestamp: flight1,
                              flight2.takeoff_timestamp: flight2}
        # pprint.pprint(self._start_beacons)
        # print(list(self._start_beacons.keys()))

        self.flight_beacon_counts = {}

        if len(self._start_beacons) == 2:
            self._earliest_time = min(list(self._start_beacons.keys()))
            self._latest_time = max(list(self._start_beacons.keys()))
            earliest_flight = self._start_beacons[self._earliest_time]
            latest_flight = self._start_beacons[self._latest_time]

            self._beacons[self._earliest_time]= {
                earliest_flight.address: {
                    'altitude': earliest_flight.last_altitude,
                    'latitude': earliest_flight.last_latitude,
                    'longitude': earliest_flight.last_longitude
                }
            }

            self.count_forwards(self._latest_time)

            self._beacons[self._latest_time]= {
                latest_flight.address: {
                    'altitude': latest_flight.last_altitude,
                    'latitude': latest_flight.last_latitude,
                    'longitude': latest_flight.last_longitude
                }
            }
        else:
            self._earliest_time = min(list(self._start_beacons.keys()))

            self._beacons[self._earliest_time]= {
                flight1.address: {
                    'altitude': flight1.last_altitude,
                    'latitude': flight1.last_latitude,
                    'longitude': flight1.last_longitude
                },
                flight2.address: {
                    'altitude': flight2.last_altitude,
                    'latitude': flight2.last_latitude,
                    'longitude': flight2.last_longitude
                }
            }

        self.check_counter_datetime = self._earliest_time

        self.flight_beacon_counts[flight1.address] = 1
        self.flight_beacon_counts[flight2.address] = 1

        log.debug('[A/T] Initial beacons: {}'.format(pprint.pformat(self._beacons)))

    def count_forwards(self, target_timestamp):
        d = datetime.timedelta(seconds=1)
        new_timestamp = list(self._beacons.keys())[-1]
        while new_timestamp <= target_timestamp:
            new_timestamp = new_timestamp + d
            self._beacons[new_timestamp] = {}

    def insert_data(self, flight, beacon):

        # when an aircraft with an aerotow launch type gets a timestamp the dict is updated

        if self.flights[flight.address].launch_rec_name and beacon['receiver_name'] != self.flights[flight.address].launch_rec_name:
            # exit early if there is a common rec name and this isn't from it
            log.info("Skipping aerotow tracking: this beacon isn't from the common receiver")
            return
        if beacon['timestamp'] < list(self._beacons.keys())[0]:
            # exit early if this is from the past
            log.info("Skipping aerotow tracking: this beacon is from before the launch was detected")
            return

        if beacon['timestamp'] not in self._beacons.keys():
            # missing timestamps between the new one and the last in the dict are added
            self.count_forwards(beacon['timestamp'])
        # if self._beacons[beacon['timestamp']]:
        try:
            # if the correct timestamp exists, just slot the data in
            self._beacons[beacon['timestamp']][flight.address] = {
                    'altitude': beacon['altitude'],
                    'latitude': beacon['latitude'],
                    'longitude': beacon['longitude']
                }
        except KeyError:
            log.info('Timestamp {} missing from aerotow beacon keys'.format(beacon['timestamp']))
            pass

        self.flight_beacon_counts[flight.address] += 1

        self.check_complete(beacon, self.flights[flight.address])

    def abort(self):
        # logging.info('[A/T] failure beacons: {}'.format(pprint.pformat(self._beacons)))
        for flight in self.flights.values():
            flight.launch_complete = True
            flight.launch_height = None

    def check_complete(self, beacon, beacon_flight):

        # every 10 seconds check the average vertical/horizontal separation for the last 10 seconds
        # if they are outside parameters, mark the involved aircraft as launched, update the launch heights

        time_since_last_check = (beacon['timestamp'] - self.check_counter_datetime).total_seconds()
        log.debug('Seconds since check time: {}'.format(time_since_last_check))
        if time_since_last_check >= 10 and self.check_failures < 5:
            log.info(pprint.pformat(self.flight_beacon_counts))
            if list(self.flight_beacon_counts.values())[0] > 10 and list(self.flight_beacon_counts.values())[0] > 10:
                # set the pair to use only the most commonly seen beacon
                flight_addresses = list(self.flights.keys())
                if not self.flights[flight_addresses[0]].launch_rec_name:
                    data = Counter(
                        [i['receiver'] for i in self.flights[flight_addresses[0]].last_pings] + [i['receiver'] for i in self.flights[flight_addresses[1]].last_pings])
                    common_rec_name = (data.most_common(1)[0][0])
                    log.info('Common receiver name for the aerotow pair is {}'.format(common_rec_name))

                    for reg in self.flights:
                        self.flights[reg].launch_rec_name = common_rec_name

                last_pings = list(self._beacons.items())[-10:]

                grouped_metrics = {}

                for _, flights in last_pings:
                    for flight in flights:
                        if not flight in grouped_metrics.keys():
                            grouped_metrics[flight] = {
                                'altitude': [flights[flight]['altitude']],
                                'latitude': [flights[flight]['latitude']],
                                'longitude': [flights[flight]['longitude']]
                            }
                        else:
                            grouped_metrics[flight]['altitude'].append(flights[flight]['altitude'])
                            grouped_metrics[flight]['latitude'].append(flights[flight]['latitude'])
                            grouped_metrics[flight]['longitude'].append(flights[flight]['longitude'])

                log.debug('[A/T] Grouped metrics: {}'.format(pprint.pformat(grouped_metrics)))

                averages = {}
                for reg, data in grouped_metrics.items():
                    averages[reg] = {
                        'altitude': mean(data['altitude']),
                        'latitude': mean(data['latitude']),
                        'longitude': mean(data['longitude'])
                    }

                log.debug('[A/T] Averages: {}'.format(pprint.pformat(averages)))

                average_addresses = list(averages.keys())
                log.info('average addresses: {}'.format(pprint.pformat(average_addresses)))

                if len(average_addresses) < 2:
                    logging.info('Lost track of an aircraft, waiting another 10 seconds')
                    self.check_failures +=1
                    self.check_counter_datetime = beacon['timestamp']
                    log.info('Check counter datetime now {}'.format(self.check_counter_datetime))
                    return
                else:
                    self.check_failures = 0

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
                            self.flights[average_addresses[0]].address if self.flights[average_addresses[0]].registration == 'UNKNOWN' else self.flights[average_addresses[0]].registration,
                            self.flights[average_addresses[1]].address if self.flights[average_addresses[1]].registration == 'UNKNOWN' else self.flights[average_addresses[1]].registration,
                            beacon_flight.takeoff_airfield,
                            vertical_separation,
                            beacon_flight.launch_height,
                            beacon_flight.launch_height * 3.281
                        ))
                    log.info('Horizontal separation was: {}'.format(horizontal_separation))
                    beacon_flight.launch_complete = True
                    beacon_flight.tug.launch_complete = True
                    return

                if horizontal_separation > 300:
                    log.info(
                        'Aerotow involving {} and {} is complete at {} with a horizontal separation of {} at a height of {} ({} ft)'.format(
                            self.flights[average_addresses[0]].address if self.flights[average_addresses[0]].registration == 'UNKNOWN' else self.flights[average_addresses[0]].registration,
                            self.flights[average_addresses[1]].address if self.flights[average_addresses[1]].registration == 'UNKNOWN' else self.flights[average_addresses[1]].registration,
                            beacon_flight.takeoff_airfield,
                            horizontal_separation,
                            beacon_flight.launch_height,
                            beacon_flight.launch_height * 3.281
                        ))
                    log.info('Vertical separation was: {}'.format(vertical_separation))
                    beacon_flight.launch_complete = True
                    beacon_flight.tug.launch_complete = True
                    return




            self.check_counter_datetime = beacon['timestamp']
            log.debug('Check counter datetime now {}'.format(self.check_counter_datetime))
        elif self.check_failures >= 5:
            # todo: switch to climb rate based a/t tracking
            log.info('abort tracking, too many failures')
            self.abort()

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