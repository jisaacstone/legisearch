#!/usr/bin/env python


def create_tables(connection):
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS events(
        id int NOT NULL,
        body int NOT NULL,
        date text NOT NULL,
        time text,
        agenda text,
        minutes text,
        minutestatus int,
        insiteurl text NOT NULL,
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS items(
        id int NOT NULL,
        eventid int NOT NULL,
        agendanumber text NOT NULL,
        actiontext text,
        title text,
        matterid int,
        matterattachments text,
        matterstatus text,
        mattertype text,
        mattertext text,
        UNIQUE(id) ON CONFLICT REPLACE,
        UNIQUE(title, agendanumber) ON CONFLICT REPLACE)
    ''')
    connection.cursor().execute('''
        CREATE TABLE IF NOT EXISTS bodies(
        id int NOT NULL,
        name text NOT NULL,
        UNIQUE(id) ON CONFLICT REPLACE)
    ''')
    connection.commit()


def data_from_db(connection):
    '''all gathered data from the sqlite db'''
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute('SELECT DISTINCT title FROM items')
    items: Mapping[str, List[Mapping[str, Any]]] = {
        r[0].lower(): [] for r in cursor.fetchall() if r[0]}
    cursor.execute('SELECT * FROM items WHERE title IS NOT NULL')
    for row in cursor.fetchall():
        items[row['title'].lower()].append({k: row[k] for k in row.keys()})
    cursor.execute('SELECT * FROM events')
    events = {e['id']: dict(**e) for e in cursor.fetchall()}
    cursor.execute('SELECT id, name FROM bodies')
    bodies = {r['id']: r['name'] for r in cursor.fetchall()}
    return items, events, bodies


def insert_events(connection, events):
    cursor = connection.cursor()
    try:
        i = None
        for i, event in enumerate(events):
            # simple progress bar
            i += 1
            if not i % 5:
                sys.stdout.write(f'\r#{i}: {event["EventId"]}   ')
            # insert event
            cursor.execute(
                'INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    event['EventId'],
                    event['EventBodyId'],
                    event['EventDate'] or '',
                    event['EventTime'] or '',
                    event['EventAgendaFile'] or '',
                    event['EventMinutesFile'],
                    event['EventMinutesStatusId'],
                    event['EventInSiteURL']
                )
            )
            # bulk insert event items
            cursor.executemany(
                'INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                ((
                    item['EventItemId'],
                    event['EventId'],
                    item['EventItemAgendaNumber'],
                    item['EventItemActionText'],
                    item['EventItemTitle'],
                    item['EventItemMatterId'],
                    item['attachments'],
                    item['EventItemMatterStatus'],
                    item['EventItemMatterType'],
                    item.get('text')
                ) for item in event['items'])
            )
        if i:
            print(f'recorded {i} events')
        else:
            print('no more events to fetch')
    finally:
        connection.commit()


def fetch_and_insert_bodies(namespace: str, connection):
    bodies = fetch_bodies(namespace)
    connection.cursor().executemany(
        'INSERT INTO bodies VALUES (?, ?)',
        ((b['BodyId'], b['BodyName']) for b in bodies)
    )
    connection.commit()
