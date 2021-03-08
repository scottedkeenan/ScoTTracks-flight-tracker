import json

import matplotlib.pyplot as plt
import matplotlib.dates
import matplotlib.dates as mdates
import datetime

import boto3


def lambda_handler(event, context):
    print(event)
    # event = json.loads(event['body'])
    s3_key = event['Records'][0]['s3']['object']['key']
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    print(s3_key)
    s3_client = boto3.client('s3')
    
    import tempfile
    tempdir = tempfile.gettempdir()
    print(tempdir)
    
    with open('{}/{}'.format(tempdir, s3_key), 'wb') as f:
        s3_client.download_fileobj(bucket_name, s3_key, f)
    
    with open('/tmp/{}'.format(s3_key), 'r') as f:
        event = json.loads(f.read())
 
        if event['data']:
            times = []
            y1 = []
            y2 = []
    
            for row in event['data']:
                times.append((row[0]))
                y1.append((float(row[1])))
                y2.append((float(row[2])))
    
            time_num = matplotlib.dates.datestr2num(times)
    
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
            plt.savefig('{}/{}-{}.png'.format(
                        '/tmp',
                        event['address'],
                        event['start_time']))
    
            plt.clf()
            plt.cla()
            plt.close()
            # Upload the file
            s3_client = boto3.client('s3')
            response = s3_client.upload_file(
                '{}/{}-{}.png'.format(
                    '/tmp',
                    event['address'],
                    event['start_time']),
                'scotttracks-graphs',
                'graphs/{}-{}.png'.format(
                    event['address'],
                    event['start_time']),
                ExtraArgs={'ContentType': 'image/png'}
                )
    
    
    
        else:
            return {
            'statusCode': 200,
            'body': json.dumps('No data found')
        }

        
