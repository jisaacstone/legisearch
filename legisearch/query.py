from typing import Mapping, Tuple, Dict, Any, AsyncGenerator
from urllib import request
from datetime import datetime, time
from dateutil.parser import parse
import sys
import json
import math
import asyncio
import httpx


# Legistar web api is documented here
# http://webapi.legistar.com/Help
# Documentation is sparse, but reading the odata spec + trial and error works
# I was not able to get the odata batch operations to work, I think it might
# be because only GET requests are allowed
# {client} in the documentation refers to "mountainview" in our case
# "Events" are meetings
# "EventItem" is a thing that happened at a meeting, could be agendized items
# or just random text like "PAGE BREAK"
# "Matters" are things the meeting body discusses or votes on
# see legistar.md for more details

# I could not find an existing Odata V3 library for python
BASEURL = 'https://webapi.legistar.com/v1/'
EVENTFIELDS = (
    'EventId',
    'EventBodyId',
    'EventDate',
    'EventTime',
    'EventAgendaFile',
    'EventMinutesFile',
    'EventMinutesStatusId',
    'EventInSiteURL')
ITEMFIELDS = (
    'EventItemId',
    'EventItemAgendaNumber',
    'EventItemActionText',
    'EventItemTitle',
    'EventItemMatterId',
    'EventItemMatterAttachments/MatterAttachmentName',
    'EventItemMatterAttachments/MatterAttachmentHyperlink',
    'EventItemMatterStatus',
    'EventItemMatterType')
TEMPLATE = 'councildoc.html.template'
FINALSTATUS = 10  # for re-downloading non-final events


def events_url(
    namespace: str,
    min_id: int = 0,
    limit: int = 1000,
    fields=EVENTFIELDS,
) -> Tuple[str, Dict[str, str]]:
    '''An assumption here is that event_id always increases'''
    url = f'{BASEURL}{namespace}/events?'
    params = {
        '$orderby': 'EventId',
        '$select': ','.join(fields),
    }
    if limit and limit < 1000:
        params['$top'] = str(limit)

    return url, params


def items_url(namespace: str, event_id: int) -> Tuple[str, Dict[str, str]]:
    ''' The data can sometimes be messy, the observed order is
    EventItemMintuesSequence but sometimes this value is null.
    '''
    # `$expand` is not supported for all relations, but the queries are faster
    # If you can use it. It only seems to work if the expand field is also
    # explicitly included in the `$select`
    url = f'{BASEURL}{namespace}/events/{event_id}/eventitems'
    params = {
        'AgendaNote': '1',
        'MinutesNote': '1',
        'Attachments': '1',
        '$expand': 'EventItemMatterAttachments',
        '$select': ','.join(ITEMFIELDS),
        '$orderby': 'EventItemMinutesSequence,EventItemAgendaSequence'
    }
    return url, params


async def fetch_event_items(
    namespace: str,
    min_id=0,
    limit=math.inf,
    fields=EVENTFIELDS,
    filter_='EventAgendaFile ne null',
) -> AsyncGenerator[Tuple[Mapping[str, Any], Mapping[str, Any]], None]:
    async with httpx.AsyncClient() as client:
        event_gen = fetch_events(
            client, namespace, min_id, limit, fields, filter_
        )
        async for event, items in fetch_items(
            client, namespace, event_gen
        ):
            yield event, items


async def fetch_events(
    client: httpx.AsyncClient,
    namespace: str,
    min_id=0,
    limit=math.inf,
    fields=EVENTFIELDS,
    filter_='EventAgendaFile ne null',
) -> AsyncGenerator[Mapping[str, Any], None]:
    '''fetches events from the legistart api

    will start at `min_id` and continue until `limit`
    '''
    if min_id:
        filter_ += f' and EventId gt {min_id}'
    url, params = events_url(namespace, min_id, limit, fields)
    if filter_:
        params['$filter'] = filter_
    omid = min_id
    response = await client.get(url, params=params)
    events = response.json()
    for event in events:
        limit -= 1
        yield event

    if limit and min_id != omid:
        async for event in fetch_events(min_id, limit):
            yield event


async def fetch_items(
    client: httpx.AsyncClient,
    namespace: str,
    event_gen
):
    futures = []
    events = []
    noitemevents = []
    async for event in event_gen:
        if not event['EventAgendaFile']:
            noitemevents.append(event)
            continue
        events.append(event)
        # fetch event items
        iurl, iparams = items_url(namespace, event['EventId'])
        futures.append(client.get(iurl, params=iparams))

    for event, item_resp in zip(events, await asyncio.gather(*futures)):
        yield (event, item_resp.json())
    for event in noitemevents:
        yield (event, [])


def format_event(
    namespace,
    event,
    items,
    fetch_matter_text=False,
    fetch_item_extra=False,
) -> Mapping[str, Any]:
    event_items = []
    # some event items are just text, and are motions or discussion
    # related to the previous item. So we keep track of the item and
    # append to it's description
    agenda_number = ''
    for item in items:
        if item['EventItemAgendaNumber']:
            agenda_number = item['EventItemAgendaNumber']
        else:
            item['EventItemAgendaNumber'] = agenda_number
        if fetch_item_extra:
            add_item_data(namespace, item)
        if fetch_matter_text:
            add_matter_data(namespace, item)
        item['attachments'] = json.dumps(
            {m['MatterAttachmentName']: m['MatterAttachmentHyperlink']
             for m in item.pop('EventItemMatterAttachments')}
        )
        possibleTexts = filter(
            None,
            (
                item['EventItemMatterType'],
                item['EventItemAgendaNumber'],
                item['EventItemTitle'],
                item['EventItemActionText'],
            )
        )
        if possibleTexts:
            item['lower_text'] = '\n'.join(possibleTexts).lower()
        else:
            item['lower_text'] = None

        event_items.append(item)

    # TODO: timezone stuff
    try:
        date = datetime.fromisoformat(event['EventDate'])
        if event['EventTime']:
            hour = parse(event['EventTime']).time()
        else:
            hour = time(12)
        dt = datetime.combine(date.date(), hour)
        event['datetime'] = dt
    except Exception as e:
        print(f'failed to parse date {event} {e}')
    event['items'] = event_items
    return event


def add_item_data(namespace, item):
    # sqlite supports json, but the python stdlib doesn't interface easily
    # so I just store as text, and use JSON.parse on the frontend
    for subcat in ['Votes', 'RollCalls']:
        url = f'{BASEURL}{namespace}/EventItems/{item["EventItemId"]}/{subcat}'
        data = json.load(request.urlopen(url))
        item[subcat] = data


def add_matter_data(namespace: str, item):
    mid = item['EventItemMatterId']
    subcats = [
        'CodeSections', 'Histories', 'Versions', 'Sponsors', 'Attachments'
    ]
    if mid:
        url = BASEURL + namespace + f'/Matters/{mid}'
        data = json.load(request.urlopen(url))
        item['Matter'] = data
        for subcat in subcats:
            url = '{BASEURL}{namespace}/Matters/{mid}/{subcat}'
            data = json.load(request.urlopen(url))
            item[subcat] = data


def fetch_bodies(namespace: str):
    '''fetch and store meeting body data. city council is 138, etc'''
    url = BASEURL + namespace + '/bodies?$select=BodyId,BodyName'
    bodies = json.load(request.urlopen(url))
    return bodies


if __name__ == '__main__':
    namespace = sys.argv[1]
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    else:
        limit = 10

    async def fetch():
        events = [e async for e in fetch_event_items(
            namespace, limit=limit
        )]
        print(json.dumps(events, indent=2))
    asyncio.run(fetch())
