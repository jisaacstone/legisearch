# -*- coding: utf-8 -*-

import re
import json
from collections import defaultdict
from sqlalchemy import select, func
from legisearch import db


async def search(namespace, search_string):
    low = search_string.lower()
    query = (
        select(db.items, db.events)
        .select_from(db.items)
        .join(db.events, db.items.c.event_id == db.events.c.id)
        .where(func.instr(db.items.c.full_text_lower, low))
    )
    async with db.new_connection(namespace) as conn:
        result = await conn.execute(query)
        for row in result:
            yield row._mapping


async def all_minutes(namespace, body_id):
    query = (
        select(db.items, db.events)
        .select_from(db.items)
        .join(db.events, db.items.c.event_id == db.events.c.id)
        .where(db.events.c.body_id == body_id)
        .order_by(db.events.c.meeting_time, db.items.c.id)
    )
    async with db.new_connection(namespace) as conn:
        result = await conn.execute(query)
        for row in result:
            yield row._mapping


async def report(namespace, body_id):
    rows = all_minutes(namespace, body_id)
    event_id = None
    titles = defaultdict(list)
    async for row in rows:
        if row['meeting_time'].year < 2023:
            continue
        if row['id_1'] != event_id:
            event_id = row['id_1']
            print()
            print(row['meeting_time'].strftime('%a %d %b %Y, %I:%M%p'))
            print(f" -- {row['title']} -- ")
        else:
            if row['agenda_number'] in ('1.', '2.'):
                continue
            print(row["full_text_lower"])
        if row.get('title') and re.match('\d\.\d', row['agenda_number']):
            titles[row['title'].strip().lower()].append(f"{row['agenda_number']}, {row['meeting_time'].year}, {row['meeting_time'].month}")

    json.dump(dict(sorted(titles.items())), sys.stdout)


if __name__ == '__main__':
    import sys, asyncio
    async def test():
        namespace = sys.argv[1]
        bid = sys.argv[2]
        await report(namespace, bid)
    asyncio.run(test())
