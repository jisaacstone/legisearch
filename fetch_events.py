#!/usr/bin/env python3

'''usage: fetch_events.py reset | fetch [limit] | generate

fetch:    - pull data for LIMIT more meetings and store in the db
generate: - create a html file with the meeting data
reset:    - drop all tables and data from the db

Recommended usage: run fetch until no more data is read, then run generate
'''

from urllib import request
import sys
import json
import math
import sqlite3

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
BASEURL = 'https://webapi.legistar.com/v1/mountainview/'
EVENTFIELDS = (
    'EventId',
    'EventBodyId',
    'EventDate',
    'EventTime',
    'EventAgendaFile',
    'EventMinutesFile',
    'EventInSiteURL')
# An assumption here is that event ids always increase
EVENTS = (
    BASEURL +
    'events?$orderby=EventId&$select=' +
    ','.join(EVENTFIELDS) +
    '&$filter=EventAgendaFile+ne+null+and+EventId+gt+{}')
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
# The data can sometimes be messy, the observed order is EventItemMintuesSequence
# but sometimes this value is null.
ITEMS = (
    BASEURL +
    'events/{}/eventitems?AgendaNote=1&MinutesNote=1&Attachments=1' +
    '&$expand=EventItemMatterAttachments&$select=' +
    ','.join(ITEMFIELDS) +
    '&$orderby=EventItemMinutesSequence,EventItemAgendaSequence')


def add_item_data(item, fetch_matter_text=False):
    matterid = item['EventItemMatterId']
    # It seems the matter text is just a repeat of the EventItemActionText
    # And fetching is slow so disabling it for now
    if matterid and fetch_matter_text:
        mattertext = ''
        matterurl = BASEURL + f'/matters/{matterid}/'
        versions = json.load(request.urlopen(matterurl + 'versions'))
        for v in versions:
            textdata = json.load(request.urlopen(matterurl + f'/texts/{v["Key"]}'))
            mattertext += textdata['MatterTextPlain']
        item['text'] = mattertext
    else:
        item['text'] = '' if fetch_matter_text else None
    # sqlite supports json, but the pysthon stdlib doesn't interface easily
    # so I just store as text, and use JSON.parse on the frontend
    item['attachments'] = json.dumps(
        {m['MatterAttachmentName']: m['MatterAttachmentHyperlink']
         for m in item.pop('EventItemMatterAttachments')}
    )
    return item


def fetch_events(min_id=0, limit=math.inf, fetch_matter_text=False):
    '''fetches events from the legistart api

    will start at `min_id` and continue until `limit`
    '''
    url = EVENTS.format(min_id)
    # max page size is 1000
    # currently there are less than 3000 items so we can read everything in 3 pages
    if limit < 1000:
        url += f'&$top={limit}'
    omid = min_id
    response = request.urlopen(url)
    for event in json.load(response):
        limit -= 1
        # fetch event items
        items = json.load(request.urlopen(ITEMS.format(event['EventId'])))
        event['items'] = []
        # some event items are just text, and are motions or discussion related to
        # the previous item. So we keep track of the item and append to it's description
        item = None
        for item_ in items:
            if item_['EventItemAgendaNumber']:
                if item:
                    event['items'].append(item)
                    item = None
                if item_['EventItemAgendaNumber'][-1] == '.' or len(item_['EventItemAgendaNumber']) == 1:
                    # skip section titles
                    continue
                item = add_item_data(item_)
            elif item and (item_['EventItemActionText'] or item_['EventItemTitle']):
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


def create_tables(connection):
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS events(
        id int NOT NULL,
        body int NOT NULL,
        date text NOT NULL,
        time text,
        agenda text,
        minutes text,
        insiteurl text NOT NULL,
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS items(
        id int NOT NULL,
        eventid int NOT NULL,
        agendanumber text NOT NULL,
        actiontext text,
        title text,
        matterid int,
        matterattachments text,
        matterstatus text,
        mattertype text,
        mattertext text,
        UNIQUE(id) ON CONFLICT REPLACE,
        UNIQUE(title, agendanumber) ON CONFLICT REPLACE)
    ''')
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS bodies(
        id int NOT NULL,
        name text NOT NULL,
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.commit()


def data_from_db(connection):
    '''all gathered data from the sqlite db'''
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute('SELECT DISTINCT title FROM items')
    items = {r[0].lower(): [] for r in cursor.fetchall() if r[0]}
    cursor.execute('SELECT * FROM items WHERE title IS NOT NULL')
    for row in cursor.fetchall():
        items[row['title'].lower()].append({k: row[k] for k in row.keys()})
    cursor.execute('SELECT * FROM events')
    events = {e['id']: dict(**e) for e in cursor.fetchall()}
    cursor.execute('SELECT id, name FROM bodies')
    bodies = {r['id']: r['name'] for r in cursor.fetchall()}
    return items, events, bodies


def insert_events(connection, events):
    cursor = connection.cursor()
    try:
        i = None
        for i, event in enumerate(events):
            # simple progress bar
            i += 1
            if not i % 5:
                sys.stdout.write(f'\r#{i}: {event["EventId"]}   ')
            # insert event
            cursor.execute(
                'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    event['EventId'],
                    event['EventBodyId'],
                    event['EventDate'] or '',
                    event['EventTime'] or '',
                    event['EventAgendaFile'] or '',
                    event['EventMinutesFile'],
                    event['EventInSiteURL']
                )
            )
            # bulk insert event items
            cursor.executemany(
                'INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                ((
                    item['EventItemId'],
                    event['EventId'],
                    item['EventItemAgendaNumber'],
                    item['EventItemActionText'],
                    item['EventItemTitle'],
                    item['EventItemMatterId'],
                    item['attachments'],
                    item['EventItemMatterStatus'],
                    item['EventItemMatterType'],
                    item['text']
                ) for item in event['items'])
            )
        if i:
            print(f'recorded {i} events')
        else:
            print('no more events to fetch')
    finally:
        connection.commit()


def fetch_bodies(connection):
    '''fetch and store meeting body data. city council is 138, etc'''
    url = BASEURL + 'bodies?$select=BodyId,BodyName'
    bodies = json.load(request.urlopen(url))
    connection.cursor().executemany(
        'INSERT INTO bodies VALUES (?, ?)',
        ((b['BodyId'], b['BodyName']) for b in bodies)
    )
    connection.commit()


def fetch_more_events(limit=100):
    '''check the max event id from the db, and fetch `limit` more events'''
    connection = sqlite3.connect('minutes.db')
    try:
        cursor = connection.cursor();
        cursor.execute('SELECT max(id) FROM events')
        maxid, = cursor.fetchone()
        print(f'fetching up to {limit} events, starting from {maxid}')
        event_iter = fetch_events(min_id=maxid, limit=limit)
        insert_events(connection, event_iter)
    finally:
        connection.close()


def reset():
    '''drop all tables and data. dangerous'''
    connection = sqlite3.connect('minutes.db')
    cursor = connection.cursor();
    cursor.execute('DROP TABLE IF EXISTS events')
    cursor.execute('DROP TABLE IF EXISTS items')
    cursor.execute('DROP TABLE IF EXISTS bodies')
    create_tables(connection)
    fetch_bodies(connection)
    connection.close()


def db_to_template():
    '''generate a all-in-one search webpage with our data embedded in

    Generated file is about 7.5M
    '''
    connection = sqlite3.connect('minutes.db')
    items, events, bodies = data_from_db(connection)
    with open('councildoc.html.template', 'r') as fob:
        html = (
            fob.read()
            .replace('<%ITEMS%>', json.dumps(items))
            .replace('<%EVENTS%>', json.dumps(events))
            .replace('<%BODIES%>', json.dumps(bodies))
        )
    with open('councildoc.html', 'w') as fob:
        fob.write(html)


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'fetch'
    if arg == 'fetch':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        fetch_more_events(limit=limit)
    elif arg == 'reset':
        reset()
    elif arg == 'generate':
        db_to_template()
    else:
        print(__doc__)
