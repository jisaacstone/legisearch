import json
import re
from collections import defaultdict
from legisearch import db
from sqlalchemy import func, select


async def search(
    namespace,
    search_string="",
    body=0,
    year=0,
    month=0,
):
    query = (
        select(db.items, db.events)
        .select_from(db.items)
        .join(db.events, db.items.c.event_id == db.events.c.id)
    )

    if search_string:
        low = search_string.lower()
        # Case-insensitive fallback: lowercase the COALESCE output completely
        query = query.where(
            func.instr(
                func.lower(
                    func.coalesce(db.items.c.full_text_lower, db.items.c.title)
                ),
                low,
            )
        )

    if year:
        if month:
            v = f"{year}-{int(month):02d}"
            ln = 8
        else:
            v = str(year)
            ln = 5
        query = query.where(func.substr(db.events.c.meeting_time, 0, ln) == v)

    async with db.new_connection(namespace) as conn:
        if body:
            result = await conn.execute(select(db.bodies))
            bodies = {int(row[1]): row[0] for row in result}
            body_id = bodies.get(body, body)
            query = query.where(db.events.c.body_id == body_id)

        print(query)
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
#        if row.get('title') and re.match('\d\.\d', row['agenda_number']):
        if row.get('title') and row.get('agenda_number') and re.match(r'\d\.\d', str(row['agenda_number'])):
            titles[row['title'].strip().lower()].append(f"{row['agenda_number']}, {row['meeting_time'].year}, {row['meeting_time'].month}")

    json.dump(dict(sorted(titles.items())), sys.stdout)


if __name__ == '__main__':
    import sys, asyncio
    async def test():
        namespace = sys.argv[1]
        bid = sys.argv[2]
        await report(namespace, bid)
    asyncio.run(test())
