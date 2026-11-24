import sqlite3

conn = sqlite3.connect("sanjose.db")
cursor = conn.cursor()

# Get 5 items regardless of whether full_text_lower is NULL or not
matches = cursor.execute("""
    SELECT events.meeting_time, bodies.name, items.agenda_number, items.title, items.full_text_lower
    FROM items
    JOIN events ON items.event_id = events.id
    LEFT JOIN bodies ON events.body_id = bodies.id
    LIMIT 5;
""").fetchall()

print(f"=== ALL UNFILTERED ITEMS ({len(matches)} found) ===")
for m in matches:
    print(f"Date: {m[0]} | Body: {m[1]} | Agenda #: {m[2]}")
    print(f"Title: {m[3]}")
    print(f"full_text_lower content: {repr(m[4])}\n")

conn.close()