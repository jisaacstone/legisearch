# -*- coding: utf-8 -*-

from typing import Mapping, AsyncGenerator
from collections import Counter
from urllib import request
from datetime import date, timedelta, datetime
from dateutil.parser import parse
from dateutil.tz import tzutc
from zoneinfo import ZoneInfo
import argparse
import json
import sys
import httpx
from icalendar import Calendar, Event
from legisearch import query


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
Agenda: {EventAgendaFile}
Web Link: {EventInSiteURL}

{items}
'''


async def fetch_bodies(
    namespace: str
) -> Mapping[str, int]:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    async with httpx.AsyncClient() as client:
        events = query.fetch_events(
            client,
            namespace,
            filter_=f"EventDate gt datetime'{yesterday}'",
            fields=('EventBodyId', 'EventBodyName')
        )
        bodycount = Counter([(e['EventBodyName'], e['EventBodyId']) async for e in events])
    return {k[0]: {'name': k[1], 'count': v} for k, v in sorted(bodycount.items())}


async def fetch_events(
    namespace: str,
    bodies=[]
) -> AsyncGenerator[Mapping[str, any], None]:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    filter_ = f"EventAgendaFile ne null and EventDate gt datetime'{yesterday}'"
    events = query.fetch_event_items(namespace, filter_=filter_, fields=EVENTFIELDS)
    async for event, items in events:
        # "IN" operator not supported in odata3, so we do in code
        if bodies and str(event['EventBodyId']) not in bodies:
            continue
        event['items'] = extract_items(items)
        yield event


def extract_items(items: Mapping[str, any]) -> str:
    '''reconstruct an agenda from the event items'''
    text = []
    for item in items:
        if item.get('EventItemTitle'):
            text.append(item['EventItemTitle'])
        if item.get('EventItemMatterAttachments'):
            for a in item['EventItemMatterAttachments']:
                text.append(f"{a['MatterAttachmentName']} {a['MatterAttachmentHyperlink']}")
    return '\n'.join(text)


def event_to_ical(event, tzinfo):
    if 'EventLocation' not in event:
        event['EventLocation'] = 'Unknown'
    if 'EventBodyName' not in event:
        event['EventBodyName'] = str(event['EventBodyId'])
    date = datetime.fromisoformat(event['EventDate'])
    time = parse(event['EventTime'])
    dt = datetime.combine(date.date(), time.time(), tzinfo=tzinfo)
    evt = Event()
    evt.add('uid', event['EventId'])
    evt.add('dtstart', dt)
    # How long are the meetings? It is unknown. Assume 2 hours?
    evt.add('dtend', dt + timedelta(hours=2))
    evt.add('summary', event['EventBodyName'] + ' Meeting')
    evt.add('location', event.get('EventLocation', ''))
    evt.add('description', DESC.format_map(event))
    if event.get('EventLastModifiedUtc'):
        evt.add('last-modified',
                parse(event['EventLastModifiedUtc']).replace(tzinfo=tzutc()))
    return evt


async def gen_ical(
    namespace='mountainview',
    timezone='America/Los_Angeles',
    bodies=None
):
    cal = Calendar()
    # cal.add('tzid', timezone)
    cal.add('procid', f'-//legiscal/{namespace}-{",".join(bodies)}//')
    tzinfo = ZoneInfo(timezone)
    async for event in fetch_events(namespace, bodies):
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
        nargs='*',
        default=[]
    )
    return parser


async def main(args=None):
    if args is None:
        args = sys.argv[1:]
    cmd = parser().parse_args(args)
    cal = await gen_ical(cmd.namespace, cmd.timezone, cmd.bodyid)
    return cal.to_ical().decode('utf8')


if __name__ == '__main__':
    import asyncio
    coroutine = main()
    print(asyncio.run(coroutine))
