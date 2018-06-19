import boto3
import datetime
import json
import re
import requests
from dateutil.parser import parse


def send_to_slack(job):
    message = dict()
    message['attachments'] = list()

    item = dict()
    item['color'] = '#36a64f'
    item['title'] = job['title']
    item['title_link'] = job['url']
    item['text'] = job['text']
    item['footer'] = 'cybersecuritycareers.net'

    fields_dict = dict()
    fields_dict['title'] = job['org']
    fields = list()
    fields.append(fields_dict)

    item['fields'] = fields
    message['attachments'].append(item)

    headers = {'Content-type': 'application/json'}

    requests.post('https://hooks.slack.com/services/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', headers=headers, data=json.dumps(message))


def parse_js(job_raw):
    job_details = dict()

    title = re.search('"\s>(.+)<\/a>', job_raw)
    #    print(job_raw)
    if title is not None:
        job_details['title'] = title.group(1)
    else:
        job_details['title'] = re.search('_blank"\s\s\>(.+)<\/a>', job_raw).group(1)

    org = re.search('warning">(.+)<\/p>\'', job_raw)
    if org is not None:
        job_details['org'] = org.group(1)
    else:
        job_details['org'] = ''

    text = job_details['text'] = re.search('"<p>(.+)<\/p><hr\/>";', job_raw)
    if text is not None:
        job_details['text'] = text.group(1)

    url = re.search('href="(.+)&qd=', job_raw)
    if url is not None:
        job_details['url'] = url.group(1)

    date = re.search('Date\(\'(.+)\'\)\.get', job_raw)
    if date is not None:
        job_details['date'] = parse(date.group(1), fuzzy=True).strftime("%Y-%m-%d")

    return job_details


def lambda_handler(event, context):
    urls = list()
    COUNTRY = "IE"
    jobs_raw = list()
    jobs_clean = list()

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('job_mon_ie')

    count = 1
    while count <= 5:
        urls.append("http://www.cybersecuritycareers.net/{}/?page={}#jobresults".format(COUNTRY, count))
        count += 1

    for url in urls:
        results = requests.get(url)

        jobs = results.text.split('var div = document.createElement("div");')
        del jobs[0]
        del jobs[-2:]
        for job in jobs:
            jobs_raw.append(job)

    for job_raw in jobs_raw:
        jobs_clean.append(parse_js(job_raw))


    for job_clean in jobs_clean:
        if job_clean['date'] == datetime.datetime.now().strftime('%Y-%m-%d'):
            response = table.get_item(
                Key={
                    'url': job_clean['url']
                }
            )
            if 'Item' not in response:
                print(send_to_slack(job_clean))
                print(table.put_item(
                    Item=job_clean
                ))

if __name__ == "__main__":
    lambda_handler('event', 'context')