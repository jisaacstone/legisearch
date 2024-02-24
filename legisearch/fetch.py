#!/usr/bin/env python3

from typing import Mapping, Any
import json
from datetime import datetime, time
from dateutil.parser import parse
from sqlalchemy import func, select, exc
from legisearch.legistar import fetch_event_items, \
    FINALSTATUS, fetch_bodies, add_item_data, add_matter_data
from legisearch import db


async def setup_db(namespace: str, conn):
    await db.recreate_tables(namespace, conn)
    await insert_bodies(namespace, conn)


async def insert_bodies(namespace: str, conn):
    bodies = fetch_bodies(namespace)
    await conn.execute(
        db.bodies.insert(),
        [{'id': int(b['BodyId']), 'name': b['BodyName'].strip()} for b in bodies]
    )


async def fetch_more_events(
    namespace: str,
    limit=100,
    refetch_nonfinal=False,
):
    '''check the max event id from the db, and fetch `limit` more events'''
    minid = None
    async with db.new_connection(namespace) as conn:
        minid = await fetch_minid(conn, refetch_nonfinal, namespace)
        if minid is None:
            minid = 0
        print(f'fetching up to {limit} {namespace} events, minid {minid}\n')
        event_item_iter = fetch_event_items(
            namespace, min_id=minid, limit=limit
        )
        inserted = 0
        async for event, items in event_item_iter:
            if not inserted % 15:
                print(f'\r{event["EventId"]} has {len(items)} items', end='')
            filtered = format_event(namespace, event, items)
            if filtered:
                await insert_event(conn, filtered)
                inserted += 1
        print(f'\rinserted {inserted} events')


async def fetch_minid(conn, refetch_nonfinal, namespace='', retry=True):
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
        return minid
    except exc.OperationalError:
        if retry:
            # probably our first run
            print('mmm, db seems missing. attempting to create')
            await setup_db(namespace, conn)
            return await fetch_minid(conn, refetch_nonfinal, False)
        else:
            raise


def format_event(
    namespace,
    event,
    items,
    fetch_matter_text=False,
    fetch_item_extra=False,
) -> Mapping[str, Any]:
    event_items = {}
    # some event items are just text, and are motions or discussion
    # related to the previous item. So we keep track of the item and
    # append to it's description
    agenda_number = ''
    for item in items:
        if not item.get('EventItemId'):
            print('item has no id')
            print(item)
            continue

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

        if agenda_number and agenda_number in items:
            append_item_data(event_items[agenda_number], item)
        else:
            event_items[agenda_number] = item

    # TODO: timezone stuff
    try:
        date = datetime.fromisoformat(event['EventDate'])
        if event['EventTime']:
            try:
                hour = parse(event['EventTime']).time()
            except Exception:
                print(f'failed to parse time for {event}, using noon')
                hour = time(12)
        else:
            hour = time(12)
        dt = datetime.combine(date.date(), hour)
        event['datetime'] = dt
    except Exception as e:
        print(f'failed to parse date {event} {e}')
    event['items'] = list(event_items.values())
    return event


def append_item_data(item_base, new_data):
    for to_merge in ('EventItemTitle', 'EventItemActionText'):
        if new_data.get(to_merge):
            if item_base.get(to_merge):
                item_base[to_merge] = f'{item_base[to_merge].trim()}\n\n{new_data[to_merge].trim()}'
            else:
                item_base[to_merge] = new_data[to_merge].trim()


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
            'minutes_url': event.get('EventMinutesFile'),
            'minutes_status': event.get('EventMinutesStatusId'),
            'insite_url': event.get('EventInSiteURL')
        }]
    )
    if event.get('items'):
        await conn.execute(
            db.items.insert(),
            [{
                'id': item['EventItemId'],
                'event_id': event['EventId'],
                'agenda_number': item['EventItemAgendaNumber'],
                'action_text': item['EventItemActionText'],
                'title': item['EventItemTitle'],
                'full_text_lower': item['lower_text'],
                'matter_id': item['EventItemMatterId'],
                'matter_attachments': item['attachments'],
                'matter_status': item['EventItemMatterStatus'],
                'matter_type': item['EventItemMatterType'],
            } for item in event['items']]
        )
