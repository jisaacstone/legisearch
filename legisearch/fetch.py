#!/usr/bin/env python3

from typing import Mapping, Any
import json
from datetime import datetime, time, timedelta
from dateutil.parser import parse
from sqlalchemy import func, select, exc
from legisearch.legistar import FAKEFINALSTATUS, FINALSTATUS, fetch_event_items, \
    FINALSTATUSES, fetch_bodies, add_item_data, add_matter_data
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
    min_id=0,
    refetch_nonfinal=False,
    check_gaps=False,
):
    '''check the max event id from the db, and fetch `limit` more events'''
    minid = None
    async with db.new_connection(namespace) as conn:
        event_item_iter = await event_item_fetch_iter(conn, refetch_nonfinal, check_gaps, namespace, limit, min_id)
        inserted = 0
        async for event, items in event_item_iter:
            try:
                filtered = format_event(namespace, event, items)
                if filtered:
                    await insert_event(conn, filtered, refetch_nonfinal)
                    inserted += 1
            except Exception:
                print('FAIL', namespace, event, items)
        print(f'\rinserted {inserted} events')


async def event_item_fetch_iter(conn, refetch_nonfinal, check_gaps, namespace, limit, min_id):
    if refetch_nonfinal:
        return await fetch_for_refetch(conn, namespace, limit, min_id)
    if check_gaps:
        return await fetch_check_gaps(conn, namespace, limit, min_id)
    if not min_id:
        min_id = await fetch_minid(conn, namespace)
    if not min_id:
        min_id = 0
    print(f'fetching up to {limit} {namespace} events, minid {min_id}\n')
    return fetch_event_items(
        namespace, min_id=min_id, limit=limit
    )


async def fetch_for_refetch(conn, namespace: str, limit: int, min_id: int):
    result = await conn.execute(
        select(db.events.c.id)
        .where(db.events.c.minutes_status.notin_(FINALSTATUSES))
        .where(db.events.c.id > min_id)
        .order_by(db.events.c.id)
        .limit(limit)
    )
    ids_to_refetch = list(result.scalars())
    print('nonfinal ids rechecking:', ids_to_refetch)
    return fetch_event_items(namespace, ids=ids_to_refetch)


async def fetch_check_gaps(conn, namespace: str, limit: int, min_id: int):
    last = None
    found = []
    min_ = min_id if min_id else 0

    result = await conn.execute(
        select(db.events.c.id)
        .where(db.events.c.id > min_)
        .order_by(db.events.c.id)
    )
    for id_, in result:
        if last is not None and id_ != last + 1:
            found += list(range(last + 1, id_))
            if len(found) > limit:
                break
        last = id_
    print('gaps to check:', found)
    return fetch_event_items(namespace, ids=found)


async def fetch_minid(conn, namespace='', retry=True):
    try:
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
            agenda_number = item['EventItemAgendaNumber'].strip()
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

        if agenda_number and agenda_number in event_items:
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
                item_base[to_merge] = f'{item_base[to_merge].strip()}\n\n{new_data[to_merge].strip()}'
            else:
                item_base[to_merge] = new_data[to_merge].strip()


async def insert_event(conn, event, refetch_nonfinal: bool = False):
    # insert event
    status = event.get('EventMinutesStatusId')
    if refetch_nonfinal and status != FINALSTATUS and event['datetime'] < datetime.now() - timedelta(days=21):
        print('faking final status for old event', event['EventId'])
        status = FAKEFINALSTATUS

    await conn.execute(
        db.events.insert(),
        [{
            'id': event['EventId'],
            'body_id': event['EventBodyId'],
            'meeting_time': event['datetime'],
            'agenda_url': event['EventAgendaFile'] or '',
            'minutes_url': event.get('EventMinutesFile'),
            'minutes_status': status,
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
                # 'full_text_lower': item['lower_text'],
                'matter_id': item['EventItemMatterId'],
                'matter_attachments': item['attachments'],
                'matter_status': item['EventItemMatterStatus'],
                'matter_type': item['EventItemMatterType'],
            } for item in event['items']]
        )
    # await conn.commit()


if __name__ == '__main__':
    import sys
    import asyncio
    from pprint import pprint
    namespace = sys.argv[1]
    minid = int(sys.argv[2])
    limit = int(sys.argv[3])

    async def fn():
        event_item_iter = fetch_event_items(
            namespace, min_id=minid, limit=limit
        )
        inserted = 0
        async for event, items in event_item_iter:
            try:
                filtered = format_event(namespace, event, items)
                pprint(filtered)
            except Exception:
                print('FAIL!', namespace, event, items)
                raise

    asyncio.run(fn())
