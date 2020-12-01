import matplotlib.pyplot as plt
import matplotlib.dates
import csv
import datetime as dt

import mysql.connector


from flight_tracker_squirreler import get_beacons_between


def draw_alt_graph(registration, data):

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

    plt.plot_date(time_num, y1, linestyle='-', label='Altitude', marker=None)
    plt.plot_date(time_num, y2, linestyle='-', label='Ground Speed', marker=None)
    plt.xlabel('time')
    plt.ylabel('Altitude in m / speed in kph')
    # plt.title('Interesting Graph\nCheck it out')
    plt.legend()
    plt.savefig('./graphs/{}-{}.png'.format(registration, times[0].strftime("%Y-%m-%d-%H:%M:%S")))

