import matplotlib.pyplot as plt
import matplotlib.dates
import csv
import datetime as dt

import mysql.connector

from flight_tracker_squirreler import get_beacons_for_address_between


def draw_alt_graph(cursor, aircraft, chart_directory):
    print(chart_directory)
    # Generate graph of flight
    # todo  - timedelta(minutes=1)
    graph_start_time = aircraft['takeoff_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
    # print("Graph start time: {}".format(graph_start_time))
    graph_end_time = aircraft['landing_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
    # print("Graph end time: {}".format(graph_end_time))

    data = get_beacons_for_address_between(cursor,
                                           aircraft['address'],
                                           graph_start_time,
                                           graph_end_time)

    # print("Graph data")
    # print(data)

    if data:
        times = []
        y1 = []
        y2 = []

        for row in data:
            times.append((row[0]))
            # times.append(dt.datetime.strptime(row[0].split(' ')[1], '%H:%M:%S'))
            y1.append((float(row[1])))
            y2.append((float(row[2])))

        time_num = matplotlib.dates.date2num(times)

        ax = plt.gca()

        print(times)

        import matplotlib.dates as mdates
        myFmt = mdates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(myFmt)

        locator = mdates.DayLocator()
        ax.xaxis.set_major_locator(locator)

        plt.plot_date(time_num, y1, linestyle='-', linewidth=1.0, label='Altitude', marker=None)
        plt.plot_date(time_num, y2, linestyle='-', linewidth=1.0, label='Ground Speed', marker=None)
        plt.xlabel('time')
        plt.ylabel('Altitude in m / speed in kph')
        # plt.title('Interesting Graph\nCheck it out')
        plt.legend()
        plt.savefig('{}/{}-{}.png'.format(chart_directory, aircraft['registration'], times[0].strftime("%Y-%m-%d-%H-%M-%S")))
        plt.clf()
        plt.cla()
        plt.close()
    else:
        print('No data found')

# import mysql.connector
# import configparser
# config = configparser.ConfigParser()
# config.read('config.ini')
#
# from flight_tracker_squirreler import add_flight, update_flight, get_currently_airborne_flights, add_beacon, get_beacons_for_address_between
#
#
# conn = mysql.connector.connect(
#     user=config['TRACKER']['database_user'],
#     password=config['TRACKER']['database_password'],
#     host=config['TRACKER']['database_host'],
#     database = config['TRACKER']['database'])
#
# import datetime
#
# from flight_tracker_squirreler import get_todays_flights, get_all_flights
#
# # flights = get_todays_flights(conn.cursor())
# flights = get_all_flights(conn.cursor())
# print(flights)
#
# for flight in flights:
#     if flight[9] and flight[10]:
#         draw_alt_graph(
#             conn.cursor(),
#             {
#                 'address': flight[2],
#                 'registration': flight[8],
#                 'takeoff_timestamp': flight[9],
#                 'landing_timestamp': flight[10],
#             },
#             config['TRACKER']['chart_directory'] + '/test'
#         )