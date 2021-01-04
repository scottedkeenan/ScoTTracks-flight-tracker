import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.dates as mdates

import mysql.connector

from flight_tracker_squirreler import get_beacons_for_address_between


def draw_alt_graph(cursor, aircraft, chart_directory):
    # Generate graph of flight
    # todo  - timedelta(minutes=1)
    graph_start_time = aircraft.takeoff_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    graph_end_time = aircraft.landing_timestamp.strftime("%Y-%m-%d %H:%M:%S")
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

        plt.plot_date(time_num, y1, linestyle='-', linewidth=1.0, label='Altitude', marker=None)
        plt.plot_date(time_num, y2, linestyle='-', linewidth=1.0, label='Ground Speed', marker=None)
        plt.xlabel('time')
        plt.ylabel('Altitude in m / speed in kph')
        # plt.title('Interesting Graph\nCheck it out')
        plt.legend()
        plt.savefig('{}/{}-{}.png'.format(chart_directory, aircraft.registration, times[0].strftime("%Y-%m-%d-%H-%M-%S")))
        plt.clf()
        plt.cla()
        plt.close()
    else:
        print('No data found')
