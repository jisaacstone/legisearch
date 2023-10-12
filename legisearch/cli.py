#!/usr/bin/env python3

import sys
import json
import sqlite3
import asyncio
import argparse
from sqlalchemy import func, select
from legisearch.query import fetch_event_items, format_event, \
    FINALSTATUS
from legisearch import db


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


async def fetch_more_events(
    namespace: str,
    limit=100,
    refetch_nonfinal=False,
):
    '''check the max event id from the db, and fetch `limit` more events'''
    minid = None
    async with db.new_connection(namespace) as conn:
        try:
            if refetch_nonfinal:
                result = await conn.exectue(
                    select(db.events)
                    .where(db.events.c.minutestatus != FINALSTATUS)
                )
            else:
                result = await conn.execute(
                    select(func.max(db.events.c.id))
                )
            minid, = result.fetchone()
        except sqlite3.OperationalError:
            # probably our first run
            print('mmm, db seems missing. please re-run')
            await db.create_tables(namespace, conn)

        if minid is None:
            minid = 0
        print(f'fetching up to {limit} {namespace} events, minid {minid}')
        event_item_iter = fetch_event_items(
            namespace, min_id=minid, limit=limit
        )
        async for event, items in event_item_iter:
            filtered = format_event(namespace, event, items)
            await insert_event(conn, filtered)


async def insert_event(conn, event):
    # insert event
    # json.dump(event, sys.stdout, indent=2, default=str)
    await conn.execute(
        db.events.insert(),
        [{
            'id': event['EventId'],
            'body_id': event['EventBodyId'],
            'meeting_time': event['datetime'],
            'agenda_url': event['EventAgendaFile'] or '',
            'minutes_url': event['EventMinutesFile'],
            'minutes_status': event['EventMinutesStatusId'],
            'insite_url': event['EventInSiteURL']
        }]
    )
    await conn.execute(
        db.items.insert(),
        [{
            'id': item['EventItemId'],
            'event_id': event['EventId'],
            'agenda_number': item['EventItemAgendaNumber'],
            'action_text': item['EventItemActionText'],
            'title': item['EventItemTitle'],
            'matter_id': item['EventItemMatterId'],
            'matter_attachments': item['attachments'],
            'matter_status': item['EventItemMatterStatus'],
            'matter_type': item['EventItemMatterType'],
        } for item in event['items']]
    )


async def reset(
    namespace: str,
):
    '''drop all tables and data. dangerous'''
    await db.recreate_tables(namespace)


async def generate(
    namespace: str,
    outfile=None,
):
    '''generate a all-in-one search webpage with our data embedded in

    Generated file is about 7.5M
    '''
    print('TODO: remake the generate fuction')


async def parse_and_run():
    args = vars(parser().parse_args())
    func = args.pop('func')
    command = args.pop('command')
    try:
        await func(**args)
    except Exception:
        print(f'failed to run {command} with {args}', file=sys.stderr)
        raise


if __name__ == '__main__':
    asyncio.run(parse_and_run())
