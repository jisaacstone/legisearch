from typing import Mapping, List, Any
from urllib import request
import sys
import json
import math
import sqlite3
import argparse


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
) -> str:
    '''An assumption here is that event_id always increases'''
    fields = ','.join(EVENTFIELDS)
    url = (
        f'{BASEURL}{namespace}/events?' +
        f'$orderby=EventId&' +
        #f'$select={fields}&' +
        f'$filter=EventAgendaFile+ne+null+and+EventId+gt+{min_id}'
    )
    if limit and limit < 1000:
        url += f'&$top={limit}'
    return url


def items_url(namespace: str, event_id: int) -> str:
    ''' The data can sometimes be messy, the observed order is
    EventItemMintuesSequence but sometimes this value is null.
    '''
    fields = ','.join(ITEMFIELDS)
    # `$expand` is not supported for all relations, but the queries are much faster
    # If you can use it. It only seems to work if the expand field is also
    # explicitly included in the `$select`
    url = (
        f'{BASEURL}{namespace}/events/{event_id}/eventitems?' +
        'AgendaNote=1&MinutesNote=1&Attachments=1&' +
        # f'$expand=EventItemMatterAttachments&$select={fields}&' +
        '$orderby=EventItemMinutesSequence,EventItemAgendaSequence'
    )
    return url


def fetch_events(
    namespace: str,
    min_id=0,
    limit=math.inf,
    fetch_matter_text=False
):
    '''fetches events from the legistart api

    will start at `min_id` and continue until `limit`
    '''
    url = events_url(namespace, min_id, limit)
    omid = min_id
    response = request.urlopen(url)
    for event in json.load(response):
        limit -= 1
        # fetch event items
        items = json.load(
            request.urlopen(
                items_url(namespace, event['EventId'])
            )
        )
        event['items'] = []
        # some event items are just text, and are motions or discussion
        # related to the previous item. So we keep track of the item and
        # append to it's description
        item = None
        for item_ in items:
            if item_['EventItemAgendaNumber']:
                if item:
                    event['items'].append(item)
                    item = None
                if (
                    item_['EventItemAgendaNumber'][-1] == '.' or
                    '.' not in item_['EventItemAgendaNumber']
                ):
                    # skip section titles
                    continue
                item = add_item_data(item_)
                add_matter_data(namespace, item)
            elif item and (
                item_['EventItemActionText'] or item_['EventItemTitle']
            ):
                # any of these could be null
                item['EventItemActionText'] = '\n'.join(filter(
                    None,
                    (
                        item['EventItemActionText'],
                        item_['EventItemTitle'],
                        item_['EventItemActionText']
                    )
                ))
        if item:
            event['items'].append(item)

        min_id = event['EventId']
        yield event
    if limit and min_id != omid:
        yield from fetch_events(min_id, limit)


def add_item_data(item):
    # sqlite supports json, but the python stdlib doesn't interface easily
    # so I just store as text, and use JSON.parse on the frontend
    item['attachments'] = json.dumps(
        {m['MatterAttachmentName']: m['MatterAttachmentHyperlink']
         for m in item.pop('EventItemMatterAttachments')}
    )
    for subcat in ['Votes', 'RollCalls']:
        url = BASEURL + namespace + f'/EventItems/{item["EventItemId"]}/{subcat}'
        data = json.load(request.urlopen(url))
        item[subcat] = data
    return item


def add_matter_data(namespace: str, item):
    mid = item['EventItemMatterId']
    if mid:
        url = BASEURL + namespace + f'/Matters/{mid}'
        data = json.load(request.urlopen(url))
        item['Matter'] = data
        for subcat in ['CodeSections', 'Histories', 'Versions', 'Sponsors', 'Attachments']:
            url = BASEURL + namespace + f'/Matters/{mid}/{subcat}'
            data = json.load(request.urlopen(url))
            item[subcat] = data


def fetch_bodies(namespace: str):
    '''fetch and store meeting body data. city council is 138, etc'''
    url = BASEURL + namespace + '/bodies?$select=BodyId,BodyName'
    bodies = json.load(request.urlopen(url))
    return bodies


if __name__ == '__main__':
    from pprint import pprint
    namespace = sys.argv[1]
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    else:
        limit = 10
    events = list(fetch_events(namespace, limit=limit))
    print(json.dumps(events, indent=2))
