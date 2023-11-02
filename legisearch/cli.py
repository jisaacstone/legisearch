#!/usr/bin/env python3

import sys
import asyncio
import argparse
from legisearch import db
from legisearch.fetch import fetch_more_events
from legisearch.search import search


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

    search_parser = subparsers.add_parser(
        'search',
        parents=[parent],
        help='search previously fetched events and items'
    )
    search_parser.add_argument(
        'search_string',
        help='string to search for',
    )
    search_parser.set_defaults(func=do_search)

    return root_parser


async def do_search(namespace, search_string):
    columns = ('body_id', 'meeting_time', 'matter_type', 'agenda_number',
               'title', 'action_text')
    print('|'.join(columns))
    async for result in search(namespace, search_string):
        print('|'.join(str(result[col]) for col in columns))


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


def main():
    asyncio.run(parse_and_run())


if __name__ == '__main__':
    main()
