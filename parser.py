#!/usr/bin/env python3

import re
import sys
import json
import sqlite3
from pathlib import Path
upper_re = re.compile(r'^(\d)\.(\d\d?)\.? ([A-Z0-9 \n:;—§\'’"/\\(),._-]+\b)', re.MULTILINE)
title_re = re.compile(r'^(\d)\.(\d\d?)\.? ([A-Za-z0-9 :;—§\'’"/\\(),._-]+\b)', re.MULTILINE)
meta_re = re.compile(r'^(\w+): (.*)$', re.MULTILINE)
METASEP='-=-=-\n'


def order_makes_sense(sect, sub, old_sect, old_sub):
    # no going backwards
    if sect < old_sect:
        print(f'going backwards', file=sys.stderr)
        return False
    # sub items should always increment by one
    if sect == old_sect and sub != old_sub + 1:
        print(f'nonmonotonic subincrement', file=sys.stderr)
        return False
    return True


def determine_best_re(text):
    '''sometimes docs have titles span across multiple lines

    if the titles are all caps, we can detect this. otherwise not
    '''
    if any(re.search('[a-z]', t.group(3)) for t in title_re.finditer(text)):
        return title_re
    return upper_re


def extract_items(minutes: str):
    text, metatext = minutes.split(METASEP)
    print('meta', metatext)
    metadata = {m.group(1): m.group(2) for m in meta_re.finditer(metatext)}

    old_sect, old_sub, old_end, item = 0, 0, 0, {}
    # When the section titles are all uppercase we can detect multiline titles
    regex = determine_best_re(text)
    for match in regex.finditer(text):
        sect = int(match.group(1))
        sub = int(match.group(2))
        if not order_makes_sense(sect, sub, old_sect, old_sub):
            print(f'possible bad match {match}', file=sys.stderr)

        if item:
            item['description'] = text[old_end:match.start()].strip()
            yield item

        item = dict(
            section=sect,
            subsection=sub,
            title=re.sub(r'\s+', ' ', match.group(3)),
            **metadata)

        old_sect, old_sub = sect, sub
        old_end = match.end()
    if item:
        item['description'] = text[old_end:].strip()
        yield item


def create_table(connection):
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS minutes(
        section int NOT NULL,
        subsection int NOT NULL,
        title text NOT NULL COLLATE NOCASE,
        description text,
        date text,
        link text,
        body text COLLATE NOCASE,
        doctype text COLLATE NOCASE,
        UNIQUE(section, subsection, title) ON CONFLICT REPLACE)
    ''')
    connection.commit()


def insert_item(cursor, item):
    cursor.execute(
        'INSERT INTO minutes VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            item['section'],
            item['subsection'],
            item['title'],
            item.get('description'),
            item.get('date'),
            item.get('link'),
            item.get('body'),
            item.get('doctype')
        )
    )


def data_from_db():
    connection = sqlite3.connect('minutes.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute('SELECT DISTINCT title FROM minutes')
    data = {r[0].lower(): [] for r in cursor.fetchall()}
    cursor.execute('SELECT * FROM minutes')
    for row in cursor.fetchall():
        data[row['title'].lower()].append({k: row[k] for k in row.keys()})
    return data


def extract_and_save(filename: str):
    connection = sqlite3.connect('minutes.db')
    create_table(connection)
    cursor = connection.cursor()
    with open(filename, 'r') as fob:
        contents = fob.read()
    for item in extract_items(contents):
        insert_item(cursor, item)
    connection.commit()


def extract_all():
    base = Path('ocr_minutes')
    for year in base.iterdir():
        for file in year.iterdir():
            print('extracting', file)
            extract_and_save(file)


def print_all():
    # for testing
    base = Path('ocr_minutes')
    for year in base.iterdir():
        for file in year.iterdir():
            print('FILE---', file)
            with open(file) as fob:
                content = fob.read()
            for item in extract_items(content):
                item.pop('description')
                print(item)


def db_to_template():
    data = data_from_db()
    strdata = json.dumps(data)
    print(strdata[:100])
    with open('minutes.html.template', 'r') as fob:
        html = fob.read().replace('<%MINUTES%>', strdata)
    with open('minutes.html', 'w') as fob:
        fob.write(html)


if __name__ == '__main__':
    action = (sys.argv + ['extract'])[1]
    if action == 'extract':
        extract_all()
    elif action == 'generate':
        db_to_template()
    else:
        print(f'''
Usage: {sys.argv[0]} ACTION
where ACTION is:

  extract   - extract data from the ocr files and instert into the sqlite db
  generate  - query data from the sqlite db and generate a static html page
''')
