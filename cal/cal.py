# -*- coding: utf-8 -*-

from urllib import request
from datetime import date, timedelta, datetime
from dateutil.parser import parse
from zoneinfo import ZoneInfo
import json
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
    'EventLastModifiedUtc'
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
    '''An assumption here is that event_id always increases'''
    # fields = ','.join(EVENTFIELDS)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    url = (
        f'{BASEURL}{namespace}/events?' +
        # f'$orderby=EventDate&$select={fields}&' +
        '$filter=EventAgendaFile+ne+null+' +
        f"and+EventDate+gt+datetime'{yesterday}'"
    )
    return url


def fetch_events(
    namespace: str,
):
    '''fetches events from the legistart api
    '''
    url = events_url(namespace)
    response = request.urlopen(url)
    for event in json.load(response):
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
            datetime.fromisoformat(event['EventLastModifiedUtc']))
    return evt


def gen_ical(
    namespace: str = 'mountainview',
    timezone: str = 'America/Los_Angeles'
):
    cal = Calendar()
    # cal.add('tzid', timezone)
    cal.add('procid', f'-//legiscal/{namespace}//')
    tzinfo = ZoneInfo(timezone)
    for event in fetch_events(namespace):
        evt = event_to_ical(event, tzinfo)
        cal.add_component(evt)
    return cal


if __name__ == '__main__':
    print(gen_ical().to_ical().decode('utf8'))
