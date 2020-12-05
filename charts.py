import matplotlib.pyplot as plt
import matplotlib.dates
import csv
import datetime as dt

import mysql.connector


from flight_tracker_squirreler import get_beacons_between


def draw_alt_graph(registration, data, chart_directory):

    times = []
    y1 = []
    y2 = []

    alt_graph = plt.figure()

    for row in data:
        times.append((row[0]))
        # times.append(dt.datetime.strptime(row[0].split(' ')[1], '%H:%M:%S'))
        y1.append((float(row[1])))
        y2.append((float(row[2])))

    time_num = matplotlib.dates.date2num(times)

    ax = alt_graph.gca()

    print(times)

    import matplotlib.dates as mdates
    myFmt = mdates.DateFormatter('%H:%M')
    ax.xaxis.set_major_formatter(myFmt)

    locator = mdates.DayLocator()
    ax.xaxis.set_major_locator(locator)

    alt_graph.plot_date(time_num, y1, linestyle='-', label='Altitude', marker=None)
    alt_graph.plot_date(time_num, y2, linestyle='-', label='Ground Speed', marker=None)
    alt_graph.xlabel('time')
    plt.ylabel('Altitude in m / speed in kph')
    # plt.title('Interesting Graph\nCheck it out')
    alt_graph.legend()
    alt_graph.savefig('{}/{}-{}.png'.format(chart_directory, registration, times[0].strftime("%Y-%m-%d-%H-%M-%S")))
    alt_graph.clear()
    plt.close(alt_graph)
