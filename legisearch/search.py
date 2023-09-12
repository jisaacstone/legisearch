#!/usr/bin/env python3

from typing import Mapping, List, Any
from urllib import request
import sys
import json
import math
import sqlite3
import argparse
from legisearch.query import fetch_events, fetch_bodies, filter_events

TEMPLATE = 'councildoc.html.template'


def parser() -> argparse.ArgumentParser:
    '''Command line useage definitions'''
    root_parser = argparse.ArgumentParser(
        prog='legisearch',
        description='legistar scraper and single-page search',
    )

    # parent has args for all commands
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        '-n', '--namespace',
        help='legistar api subdomain and db name',
        default='mountainview'
    )
    subparsers = root_parser.add_subparsers(
        required=True,
        dest='command',
    )

    # individual command parsers
    fetch_parser = subparsers.add_parser(
        'fetch',
        parents=[parent],
        help='fetch new events from the legistar api'
    )
    fetch_parser.add_argument(
        '-l', '--limit',
        help='max number of events to fetch',
        type=int,
        default=50
    )
    fetch_parser.add_argument(
        '--refetch-nonfinal',
        help='re-fetch events which did not have final minutes',
        action='store_true'
    )
    fetch_parser.set_defaults(func=fetch_more_events)

    reset_parser = subparsers.add_parser(
        'reset',
        parents=[parent],
        help='wipe and re-create the database'
    )
    reset_parser.set_defaults(func=reset)

    generate_parser = subparsers.add_parser(
        'generate',
        parents=[parent],
        help='generate the static search html page'
    )
    generate_parser.add_argument(
        '-o', '--outfile',
        help='name of the html page to generate',
    )
    generate_parser.set_defaults(func=generate)
    return root_parser


def create_tables(connection):
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS events(
        id int NOT NULL,
        body int NOT NULL,
        date text NOT NULL,
        time text,
        agenda text,
        minutes text,
        minutestatus int,
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
    items: Mapping[str, List[Mapping[str, Any]]] = {
        r[0].lower(): [] for r in cursor.fetchall() if r[0]}
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
                'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    event['EventId'],
                    event['EventBodyId'],
                    event['EventDate'] or '',
                    event['EventTime'] or '',
                    event['EventAgendaFile'] or '',
                    event['EventMinutesFile'],
                    event['EventMinutesStatusId'],
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
                    item.get('text')
                ) for item in event['items'])
            )
        if i:
            print(f'recorded {i} events')
        else:
            print('no more events to fetch')
    finally:
        connection.commit()


def fetch_and_insert_bodies(namespace: str, connection):
    bodies = fetch_bodies(namespace)
    connection.cursor().executemany(
        'INSERT INTO bodies VALUES (?, ?)',
        ((b['BodyId'], b['BodyName']) for b in bodies)
    )
    connection.commit()


# COMMAND ENTRY POINTS #


def fetch_more_events(
    namespace: str,
    limit=100,
    refetch_nonfinal=False,
):
    '''check the max event id from the db, and fetch `limit` more events'''
    connection = sqlite3.connect(f'{namespace}.db')
    minid = None
    try:
        cursor = connection.cursor()
        try:
            if refetch_nonfinal:
                cursor.execute(
                    'SELECT max(id) FROM events WHERE minutestatus <> ?',
                    [FINALSTATUS]
                )
            else:
                cursor.execute('SELECT max(id) FROM events')
            minid, = cursor.fetchone()
        except sqlite3.OperationalError:
            # probably our first run
            create_tables(connection)
            fetch_bodies(namespace, connection)

        if minid is None:
            minid = 0
        print(f'fetching up to {limit} {namespace} events, minid {minid}')
        event_iter = filter_events(fetch_events(namespace, min_id=minid, limit=limit))
        insert_events(connection, event_iter)
    finally:
        connection.close()


def reset(
    namespace: str,
):
    '''drop all tables and data. dangerous'''
    connection = sqlite3.connect(f'{namespace}.db')
    cursor = connection.cursor()
    cursor.execute('DROP TABLE IF EXISTS events')
    cursor.execute('DROP TABLE IF EXISTS items')
    cursor.execute('DROP TABLE IF EXISTS bodies')
    create_tables(connection)
    fetch_and_insert_bodies(namespace, connection)
    connection.close()


def generate(
    namespace: str,
    outfile=None,
):
    '''generate a all-in-one search webpage with our data embedded in

    Generated file is about 7.5M
    '''
    connection = sqlite3.connect(f'{namespace}.db')
    if outfile is None:
        outfile = f'{namespace}.html'
    items, events, bodies = data_from_db(connection)
    with open(TEMPLATE, 'r') as fob:
        html = (
            fob.read()
            .replace('<%NAMESPACE%>', namespace)
            .replace('<%ITEMS%>', json.dumps(items))
            .replace('<%EVENTS%>', json.dumps(events))
            .replace('<%BODIES%>', json.dumps(bodies))
        )
    with open(outfile, 'w') as fob:
        fob.write(html)


def parse_and_run():
    args = vars(parser().parse_args())
    func = args.pop('func')
    command = args.pop('command')
    try:
        func(**args)
    except Exception:
        print(f'failed to run {command} with {args}', file=sys.stderr)
        raise


if __name__ == '__main__':
    parse_and_run()
