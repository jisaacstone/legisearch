#!/usr/bin/env python3

from urllib import request
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
    'events?$orderby=EventId&$filter=EventId+gt+{}&$select=' +
    ','.join(EVENTFIELDS) +
    '&$filter=EventAgendaFile+ne+null')
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
    '&$select=' +
    ','.join(ITEMFIELDS) +
    '&$expand=EventItemMatterAttachments')


def add_item_data(item):
    matterid = item['EventItemMatterId']
    mattertext = ''
    if matterid:
        matterurl = BASEURL + f'/matters/{matterid}/'
        versions = json.load(request.urlopen(matterurl + 'versions'))
        for v in versions:
            textdata = json.load(request.urlopen(matterurl + f'/texts/{v["Key"]}'))
            mattertext += textdata['MatterTextPlain']
    item['text'] = mattertext
    item['attachments'] = json.dumps(
        {m['MatterAttachmentName']: m['MatterAttachmentHyperlink']
         for m in item.pop('EventItemMatterAttachments')}
    )
    return item


def events(min_id=0, limit=math.inf):
    url = EVENTS.format(min_id)
    if limit < 1000:
        url += f'&$top={limit}'
    response = request.urlopen(EVENTS.format(min_id))
    omid = min_id
    event = None
    for event in json.load(response):
        limit -= 1
        print(ITEMS.format(event['EventId']))
        items = json.load(request.urlopen(ITEMS.format(event['EventId'])))
        event['items'] = []
        item = None
        for item_ in items:
            if item_['EventItemAgendaNumber']:
                if item:
                    event['items'].append(item)
                    item = None
                if item_['EventItemAgendaNumber'][-1] == '.':
                    # skip section titles
                    continue
                item = add_item_data(item_)
            elif item:
                text = item_['EventItemActionText'] or item_['EventItemTitle']
                print('funitem', item['EventItemAgendaNumber'], text)
                if text:
                    if item['EventItemActionText']:
                        item['EventItemActionText'] += '\n' + text
                    else:
                        item['EventItemActionText'] = text
        if item:
            event['items'].append(item)

        min_id = event['EventId']
        yield event
    print(limit)
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
    connection.commit()


def insert_events(connection, events):
    cursor = connection.cursor()
    for event in events:
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
    connection.commit()


if __name__ == '__main__':
    connection = sqlite3.connect('minutes.db')
    connection.cursor().execute('DROP TABLE items')
    create_tables(connection)
    dz = dict(zip('abc', (events(limit=1))))
    insert_events(connection, dz.values())
