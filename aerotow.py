"""
Defines a class representing an aerotow involving two Flights
Provides functions for updating, completing and aborting aerotow tracking
"""

import datetime
import os
import pprint
import logging
from statistics import mean

from collections import Counter
from geopy import distance as measure_distance

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class Aerotow:
    """
    Defines a class representing an aerotow involving two Flights
    Provides functions for updating, completing and aborting aerotow tracking
    """
    def __init__(self, flight1, flight2):
        log.info('Creating new AT object')

        self.flights = {
            flight1.address: flight1,
            flight2.address:  flight2
        }

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

            self._beacons[self._earliest_time] = {
                earliest_flight.address: {
                    'altitude': earliest_flight.last_altitude,
                    'latitude': earliest_flight.last_latitude,
                    'longitude': earliest_flight.last_longitude
                }
            }

            self.count_forwards(self._latest_time)

            self._beacons[self._latest_time] = {
                latest_flight.address: {
                    'altitude': latest_flight.last_altitude,
                    'latitude': latest_flight.last_latitude,
                    'longitude': latest_flight.last_longitude
                }
            }
        else:
            self._earliest_time = min(list(self._start_beacons.keys()))

            self._beacons[self._earliest_time] = {
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

        log.debug('[A/T] Initial beacons: %s', pprint.pformat(self._beacons))

    def count_forwards(self, target_timestamp):
        """
        Counts forwards in 1 second increments from the last timestamp in _beacons keys
        until the target timestamp is reached.
        Once reached a the target timestamp is added to _beacons as a key with an empty
        dict as the value.
        :param target_timestamp: A Timestamp object, the target time to be adding to _beacons as a key
        :return: None
        """
        delta = datetime.timedelta(seconds=1)
        new_timestamp = list(self._beacons.keys())[-1]
        while new_timestamp <= target_timestamp:
            new_timestamp = new_timestamp + delta
            self._beacons[new_timestamp] = {}

    def insert_data(self, flight, beacon):
        """
        When an flight with an aerotow launch type gets a beacon with a new timestamp, the _beacons dict is updated
        in the appropriate time slot with an entry for this flight
        :param flight: The flight object which is updating the aerotow object
        :param beacon: The ogn beacon data containing the timestamp
        :return: None
        """

        # when an aircraft with an aerotow launch type gets a timestamp the dict is updated

        if (self.flights[flight.address].launch_rec_name
                and beacon['receiver_name'] != self.flights[flight.address].launch_rec_name):
            # exit early if there is a common rec name and this isn't from it
            log.info("Skipping aerotow tracking: this beacon isn't from the common receiver")
            return
        if beacon['timestamp'] < list(self._beacons.keys())[0]:
            # exit early if this is from the past
            log.info(
                "Skipping aerotow tracking: this beacon is from before the launch was detected")
            return

        if beacon['timestamp'] not in self._beacons.keys():
            # missing timestamps between the new one and the last in the dict are added
            self.count_forwards(beacon['timestamp'])
        try:
            # if the correct timestamp exists, just slot the data in
            self._beacons[beacon['timestamp']][flight.address] = {
                    'altitude': beacon['altitude'],
                    'latitude': beacon['latitude'],
                    'longitude': beacon['longitude']
                }
        except KeyError:
            log.info('Timestamp %s missing from aerotow beacon keys', beacon['timestamp'])

        self.flight_beacon_counts[flight.address] += 1

        self.check_complete(beacon)

    def abort(self):
        """
        Aborts the aerotow by setting each Flight's launch_complete attribute to True and
        their launch heights to None
        :return: None
        """
        logging.debug('[A/T] failure beacons: %s', pprint.pformat(self._beacons))
        for flight in self.flights.values():
            flight.launch_complete = True
            flight.launch_height = None

    def check_complete(self, beacon):
        """
        Every 10 seconds check the average vertical/horizontal separation for the last 10 seconds
        if they are outside parameters, mark the involved aircraft as launch completed
        and then update the launch heights
        :param beacon: Beacon containing flight data and the timestamp which may trigger the check
        :return: None
        """
        time_since_last_check = (beacon['timestamp'] - self.check_counter_datetime).total_seconds()
        if time_since_last_check >= 10 and self.check_failures < 5:
            log.info(pprint.pformat(self.flight_beacon_counts))
            if (list(self.flight_beacon_counts.values())[0] > 10
                    and list(self.flight_beacon_counts.values())[0] > 10):
                # set the pair to use only the most commonly seen beacon
                flight_addresses = list(self.flights.keys())
                if not self.flights[flight_addresses[0]].launch_rec_name:
                    data = Counter(
                        [i['receiver']for i
                         in self.flights[flight_addresses[0]].last_pings] +
                        [i['receiver'] for i in self.flights[flight_addresses[1]].last_pings])
                    common_rec_name = (data.most_common(1)[0][0])
                    log.info('Common receiver name for the aerotow pair is %s', common_rec_name)

                    for reg in self.flights:
                        self.flights[reg].launch_rec_name = common_rec_name

                last_pings = list(self._beacons.items())[-10:]

                grouped_metrics = {}

                for _, flights in last_pings:
                    for flight in flights:
                        if flight not in grouped_metrics.keys():
                            grouped_metrics[flight] = {
                                'altitude': [flights[flight]['altitude']],
                                'latitude': [flights[flight]['latitude']],
                                'longitude': [flights[flight]['longitude']]
                            }
                        else:
                            grouped_metrics[flight]['altitude'].append(flights[flight]['altitude'])
                            grouped_metrics[flight]['latitude'].append(flights[flight]['latitude'])
                            grouped_metrics[flight]['longitude'].append(flights[flight]['longitude'])

                log.debug('[A/T] Grouped metrics: %s', pprint.pformat(grouped_metrics))

                averages = {}
                for reg, data in grouped_metrics.items():
                    averages[reg] = {
                        'altitude': mean(data['altitude']),
                        'latitude': mean(data['latitude']),
                        'longitude': mean(data['longitude'])
                    }

                log.debug('[A/T] Averages: %s', pprint.pformat(averages))

                average_addresses = list(averages.keys())
                log.info('average addresses: %s', pprint.pformat(average_addresses))

                if len(average_addresses) < 2:
                    logging.info('Lost track of an aircraft, waiting another 10 seconds')
                    self.check_failures += 1
                    self.check_counter_datetime = beacon['timestamp']
                    log.info('Check counter datetime now %s', self.check_counter_datetime)
                    return
                self.check_failures = 0

                vertical_separation = (averages[average_addresses[0]]['altitude']
                                       - averages[average_addresses[1]]['altitude'])
                horizontal_separation = measure_distance.distance(
                    (averages[average_addresses[0]]['latitude'],
                     averages[average_addresses[0]]['longitude']),
                    (averages[average_addresses[1]]['latitude'],
                     averages[average_addresses[1]]['longitude'])
                ).meters

                # Check vertical separation with tug/other in pair
                if vertical_separation > 50 or vertical_separation < -50:
                    log.info(
                        'Aerotow involving %s and %s is complete at %s'
                        'with a vertical separation of %s at a height of %s (%s ft)',
                        self.flights[average_addresses[0]].address
                        if self.flights[average_addresses[0]].registration == 'UNKNOWN'
                        else self.flights[average_addresses[0]].registration,
                        self.flights[average_addresses[1]].address
                        if self.flights[average_addresses[1]].registration == 'UNKNOWN'
                        else self.flights[average_addresses[1]].registration,
                        self.flights[beacon['address']].takeoff_airfield,
                        vertical_separation,
                        self.flights[beacon['address']].launch_height,
                        self.flights[beacon['address']].launch_height * 3.281
                        )
                    log.info('Horizontal separation was: %s', horizontal_separation)
                    for flight in self.flights:
                        flight.launch_complete = True
                    return

                if horizontal_separation > 300:
                    log.info(
                        'Aerotow involving %s and %s is complete at %s '
                        'with a horizontal separation of %s at a height of %s (%s ft)',
                        self.flights[average_addresses[0]].address
                        if self.flights[average_addresses[0]].registration == 'UNKNOWN'
                        else self.flights[average_addresses[0]].registration,
                        self.flights[average_addresses[1]].address
                        if self.flights[average_addresses[1]].registration == 'UNKNOWN'
                        else self.flights[average_addresses[1]].registration,
                        self.flights[beacon['address']].takeoff_airfield,
                        vertical_separation,
                        self.flights[beacon['address']].launch_height,
                        self.flights[beacon['address']].launch_height * 3.281
                        )
                    for flight in self.flights:
                        flight.launch_complete = True
                    return

            self.check_counter_datetime = beacon['timestamp']
            log.debug('Check counter datetime now %s', self.check_counter_datetime)
        elif self.check_failures >= 5:
            # todo: switch to climb rate based a/t tracking
            log.info('abort tracking, too many failures')
            self.abort()

# work out which is in front (tug)
# update the aircraft with their types
