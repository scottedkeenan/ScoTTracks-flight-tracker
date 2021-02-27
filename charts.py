import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.dates as mdates
import datetime

import mysql.connector

from flight_tracker_squirreler import get_beacons_for_address_between


def draw_alt_graph(cursor, aircraft, chart_directory):
    # Generate graph of flight
    graph_start_time = (aircraft.takeoff_timestamp - datetime.timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    graph_end_time = (aircraft.landing_timestamp + datetime.timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    data = get_beacons_for_address_between(cursor,
                                           aircraft.address,
                                           graph_start_time,
                                           graph_end_time)
    if data:
        times = []
        y1 = []
        y2 = []

        for row in data:
            times.append((row[0]))
            y1.append((float(row[1])))
            y2.append((float(row[2])))

        time_num = matplotlib.dates.date2num(times)

        ax = plt.gca()

        myFmt = mdates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(myFmt)

        locator = mdates.DayLocator()
        ax.xaxis.set_major_locator(locator)

        plt.plot_date(time_num, y1, linestyle='-', linewidth=1.0, label='Altitude', marker='.', ms = 3, mec = 'r', mfc = 'r')
        plt.plot_date(time_num, y2, linestyle='-', linewidth=1.0, label='Ground Speed', marker='.', ms = 3, mec = 'r', mfc = 'r')
        plt.xlabel('time')
        plt.ylabel('Altitude in m / speed in kph')
        # plt.title('Interesting Graph\nCheck it out')
        plt.legend()
        plt.grid(True)
        plt.savefig('{}/{}-{}.png'.format(chart_directory,
                                          aircraft.registration if aircraft.registration != 'UNKNOWN' else aircraft.address ,
                                          aircraft.takeoff_timestamp.strftime("%Y-%m-%d-%H-%M-%S")))

        plt.clf()
        plt.cla()
        plt.close()
    else:
        print('No data found')


def draw_alt_graph_for_address_between(cursor, address, graph_start_time, graph_end_time, chart_directory):
    # Generate graph of flight
    # todo  - timedelta(minutes=1)
    data = get_beacons_for_address_between(cursor,
                                           address,
                                           graph_start_time,
                                           graph_end_time)
    lowest_alt = 10000000
    speed = None

    if data:
        times = []
        y1 = []
        y2 = []

        for row in data:
            times.append((row[0]))
            y1.append((float(row[1])))
            y2.append((float(row[2])))

            if float(row[1]) < lowest_alt:

                print('=========')
                lowest_alt = float(row[1])
                speed = row[2]
                print(lowest_alt)
                print(speed)
                print('=========')

        time_num = matplotlib.dates.date2num(times)

        ax = plt.gca()

        myFmt = mdates.DateFormatter('%H:%M')
        ax.xaxis.set_major_formatter(myFmt)

        locator = mdates.DayLocator()
        ax.xaxis.set_major_locator(locator)

        plt.plot_date(time_num, y1, linestyle='-', linewidth=1.0, label='Altitude', marker='.', ms = 3, mec = 'r', mfc = 'r')
        plt.plot_date(time_num, y2, linestyle='-', linewidth=1.0, label='Ground Speed', marker=None)
        plt.xlabel('time')
        plt.ylabel('Altitude in m / speed in kph')
        # plt.title('Interesting Graph\nCheck it out')
        plt.legend()
        plt.savefig('{}/{}-{}.png'.format(chart_directory,
                                          address ,
                                          times[0].strftime("%Y-%m-%d-%H-%M-%S")))
        plt.clf()
        plt.cla()
        plt.close()


    else:
        print('No data found')

# import configparser
#
# config = configparser.ConfigParser()
# config.read('config.ini')
#
# def make_database_connection(retry_counter=0):
#     if retry_counter > 5:
#         return
#     try:
#         conn = mysql.connector.connect(
#             user=config['TRACKER']['database_user'],
#             password=config['TRACKER']['database_password'],
#             host=config['TRACKER']['database_host'],
#             database=config['TRACKER']['database'])
#         return conn
#     except mysql.connector.Error as err:
#         retry_counter += 1
#         return make_database_connection(retry_counter)
#
# db_conn = make_database_connection()
# draw_alt_graph_for_address_between(db_conn.cursor(), 'DDE1EC', '2021-02-18 11:56:00', '2021-02-18 12:15:00', './public_html/graphs/debug')
