# -*- coding: utf-8 -*-

from urllib import request
from datetime import date, timedelta, datetime
from dateutil.parser import parse
from dateutil.tz import tzutc
from zoneinfo import ZoneInfo
import argparse
import json
import sys
from icalendar import Calendar, Event


BASEURL = 'https://webapi.legistar.com/v1/'
EVENTFIELDS = (
    'EventId',
    'EventDate',
    'EventTime',
    'EventLocation',
    'EventBodyId',
    'EventBodyName',
    'EventAgendaStatusName',
    'EventLastModifiedUtc',
    'EventAgendaFile',
    'EventInSiteURL')
DESC = '''Meeting of {EventBodyName}
{EventTime} at {EventLocation}
{EventAgendaStatusName} Agenda: {EventAgendaFile}
Web Link: {EventInSiteURL}
'''


def events_url(
    namespace: str,
) -> str:
    fields = ','.join(EVENTFIELDS)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    url = (
        f'{BASEURL}{namespace}/events?' +
        f'$orderby=EventDate&$select={fields}&' +
        '$filter=EventAgendaFile+ne+null+' +
        f"and+EventDate+gt+datetime'{yesterday}'"
    )
    return url


def fetch_events(
    namespace: str,
    bodys
):
    url = events_url(namespace)
    response = request.urlopen(url)
    for event in json.load(response):
        # "IN" operator not supported in odata3, so we do in code
        if bodys and str(event['EventBodyId']) not in bodys:
            continue
        yield event


def event_to_ical(event, tzinfo):
    date = datetime.fromisoformat(event['EventDate'])
    time = parse(event['EventTime'])
    dt = datetime.combine(date.date(), time.time(), tzinfo=tzinfo)
    evt = Event()
    evt.add('uid', event['EventId'])
    evt.add('dtstart', dt)
    # How long are the meetings? It is unknown. Assume 2 hours?
    evt.add('dtend', dt + timedelta(hours=2))
    evt.add('summary', event['EventBodyName'] + ' Meeting')
    evt.add('location', event['EventLocation'])
    evt.add('description', DESC.format_map(event))
    evt.add('last-modified',
            parse(event['EventLastModifiedUtc']).replace(tzinfo=tzutc()))
    return evt


def gen_ical(
    namespace='mountainview',
    timezone='America/Los_Angeles',
    bodys=None
):
    cal = Calendar()
    # cal.add('tzid', timezone)
    cal.add('procid', f'-//legiscal/{namespace}//')
    tzinfo = ZoneInfo(timezone)
    for event in fetch_events(namespace, bodys):
        evt = event_to_ical(event, tzinfo)
        cal.add_component(evt)
    return cal


def parser() -> argparse.ArgumentParser:
    '''Command line useage definitions'''
    parser = argparse.ArgumentParser(
        prog='legical',
        description='turn legistar events into ics calendar',
    )

    parser.add_argument(
        'namespace',
        help='legistar api subdomain and db name',
    )

    parser.add_argument(
        '-t', '--timezone',
        help='tz database style timezone',
        default='America/Los_Angeles'
    )

    parser.add_argument(
        '-b', '--bodyid',
        help='only show selected meeting body events',
        nargs='*'
    )
    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    cmd = parser().parse_args(args)
    print(gen_ical(cmd.namespace, cmd.timezone, cmd.bodyid).to_ical().decode('utf8'))


if __name__ == '__main__':
    main()
