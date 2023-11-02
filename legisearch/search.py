# -*- coding: utf-8 -*-

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


if __name__ == '__main__':
    import sys, asyncio
    async def test():
        namespace = sys.argv[1]
        query = sys.argv[2]
        async for result in search(namespace, query):
            print(result)
    asyncio.run(test())
