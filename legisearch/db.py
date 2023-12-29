# -*- coding: utf-8 -*-

from contextlib import asynccontextmanager
from sqlalchemy import Table, Column, MetaData, Integer, DateTime, \
    Text, UniqueConstraint
from sqlalchemy.ext.asyncio import create_async_engine


meta = MetaData()
events = Table(
    'events',
    meta,
    Column('id', Integer, nullable=False),
    Column('body_id', Integer, nullable=False),
    Column('meeting_time', DateTime, nullable=False),
    Column('agenda_url', Text),
    Column('minutes_url', Text),
    Column('minutes_status', Integer),
    Column('insite_url', Text),
    UniqueConstraint('id', sqlite_on_conflict='REPLACE')
)
items = Table(
    'items',
    meta,
    Column('id', Integer, nullable=False),
    Column('event_id', Integer, nullable=False),
    Column('agenda_number', Text),
    Column('action_text', Text(collation='nocase')),
    Column('title', Text(collation='nocase')),
    Column('full_text_lower', Text),
    Column('matter_id', Integer),
    Column('matter_status', Text),
    Column('matter_attachments', Text),
    Column('matter_type', Text),
    UniqueConstraint('id', sqlite_on_conflict='REPLACE')
)
bodies = Table(
    'bodies',
    meta,
    Column('id', Integer, nullable=False),
    Column('name', Text, nullable=False),
    UniqueConstraint('id', sqlite_on_conflict='REPLACE')
)


async def recreate_tables(namespace):
    async with new_connection(namespace) as conn:
        await conn.run_sync(meta.drop_all)
        await conn.run_sync(meta.create_all)


async def create_tables(namespace, conn=None):
    if conn:
        await conn.run_sync(meta.create_all)
    else:
        async with new_connection(namespace) as conn:
            await conn.run_sync(meta.create_all)


def create_engine(namespace):
    engine = create_async_engine(f'sqlite+aiosqlite:///{namespace}.db')
    return engine


@asynccontextmanager
async def new_connection(namespace):
    engine = create_engine(namespace)
    async with engine.begin() as conn:
        yield conn
    await engine.dispose()


if __name__ == '__main__':
    import sys, asyncio
    args = sys.argv + ['mountainview']
    asyncio.run(create_tables(args[1]))
