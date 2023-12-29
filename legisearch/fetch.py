#!/usr/bin/env python3

from sqlalchemy import func, select, exc
from legisearch.query import fetch_event_items, format_event, \
    FINALSTATUS
from legisearch import db


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
        print(f'fetching up to {limit} {namespace} events, minid {minid}')
        event_item_iter = fetch_event_items(
            namespace, min_id=minid, limit=limit
        )
        async for event, items in event_item_iter:
            filtered = format_event(namespace, event, items)
            await insert_event(conn, filtered)


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
            await db.create_tables(namespace, conn)
            return await fetch_minid(conn, refetch_nonfinal, False)
        else:
            raise


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
