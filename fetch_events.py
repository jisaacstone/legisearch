#!/usr/bin/env python3

from urllib import request
import sys
import json
import math
import sqlite3

BASEURL = 'https://webapi.legistar.com/v1/mountainview/'
EVENTFIELDS = (
    'EventId',
    'EventBodyId',
    'EventDate',
    'EventTime',
    'EventAgendaFile',
    'EventMinutesFile',
    'EventInSiteURL')
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
ITEMS = (
    BASEURL +
    'events/{}/eventitems?AgendaNote=1&MinutesNote=1&Attachments=1' +
    '&$expand=EventItemMatterAttachments&$select=' +
    ','.join(ITEMFIELDS) +
    '&$orderby=EventItemMinutesSequence,EventItemAgendaSequence')


def add_item_data(item, fetch_matter_text=False):
    matterid = item['EventItemMatterId']
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
    item['attachments'] = json.dumps(
        {m['MatterAttachmentName']: m['MatterAttachmentHyperlink']
         for m in item.pop('EventItemMatterAttachments')}
    )
    return item


def fetch_events(min_id=0, limit=math.inf, fetch_matter_text=False):
    url = EVENTS.format(min_id)
    if limit < 1000:
        url += f'&$top={limit}'
    print('url', url)
    response = request.urlopen(url)
    omid = min_id
    event = None
    for event in json.load(response):
        limit -= 1
        items = json.load(request.urlopen(ITEMS.format(event['EventId'])))
        event['items'] = []
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
        yield from events(min_id, limit)


def create_tables(connection):
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS events(
        id int NOT NULL,
        body int NOT NULL,
        date text NOT NULL,
        time text NOT NULL,
        agenda text NOT NULL,
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
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS bodies(
        id int NOT NULL,
        name text NOT NULL,
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.commit()


def data_from_db(connection):
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
        for i, event in enumerate(events):
            if not i % 5:
                sys.stdout.write(f'\r#{i}: {event["EventId"]}   ')
            cursor.execute(
                'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    event['EventId'],
                    event['EventBodyId'],
                    event['EventDate'],
                    event['EventTime'],
                    event['EventAgendaFile'],
                    event['EventMinutesFile'],
                    event['EventInSiteURL']
                )
            )
            cursor.executemany(
                'INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                ((
                    i['EventItemId'],
                    event['EventId'],
                    i['EventItemAgendaNumber'],
                    i['EventItemActionText'],
                    i['EventItemTitle'],
                    i['EventItemMatterId'],
                    i['attachments'],
                    i['EventItemMatterStatus'],
                    i['EventItemMatterType'],
                    i['text']
                ) for i in event['items'])
            )
    finally:
        connection.commit()


def fetch_bodies(connection):
    url = BASEURL + 'bodies?$select=BodyId,BodyName'
    bodies = json.load(request.urlopen(url))
    connection.cursor().executemany(
        'INSERT INTO bodies VALUES (?, ?)',
        ((b['BodyId'], b['BodyName']) for b in bodies)
    )
    connection.commit()


def fetch_more_events(limit=100):
    connection = sqlite3.connect('minutes.db')
    try:
        cursor = connection.cursor();
        cursor.execute('SELECT max(id) FROM events')
        maxid, = cursor.fetchone()
        print(f'fetching {limit} events, starting from {maxid}')
        event_iter = fetch_events(min_id=maxid, limit=limit)
        insert_events(connection, event_iter)
    finally:
        connection.close()


def reset():
    connection = sqlite3.connect('minutes.db')
    cursor = connection.cursor();
    cursor.execute('DROP TABLE IF EXISTS events')
    cursor.execute('DROP TABLE IF EXISTS items')
    cursor.execute('DROP TABLE IF EXISTS bodies')
    create_tables(connection)
    fetch_bodies(connection)
    connection.close()


def db_to_template():
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
    arg = sys.argv[-1]
    if arg == 'fetch':
        fetch_more_events(limit=50)
    elif arg == 'reset':
        reset()
    elif arg == 'generate':
        db_to_template()
