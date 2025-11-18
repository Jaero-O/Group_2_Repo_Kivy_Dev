"""
inspect_db.py

Usage:
    python scripts/inspect_db.py [--db PATH]

If --db is not provided the script will look for the DB in common locations:
 - ./mangofy.db
 - %APPDATA%/mangofy/mangofy.db (Windows)
 - ~/.config/mangofy/mangofy.db (Linux)
 - ~/Library/Application Support/mangofy/mangofy.db (macOS)

The script prints the schema, table row counts and up to 5 sample rows per table.
"""
import sqlite3
import os
import sys
import json

COMMON_LOCATIONS = []
if sys.platform == 'win32':
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.join(os.environ.get('APPDATA', ''), 'mangofy', 'mangofy.db')
    ]
elif sys.platform == 'darwin':
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.expanduser('~/Library/Application Support/mangofy/mangofy.db')
    ]
else:
    COMMON_LOCATIONS = [
        os.path.join(os.getcwd(), 'mangofy.db'),
        os.path.expanduser('~/.config/mangofy/mangofy.db')
    ]


def find_db(provided_path=None):
    if provided_path:
        if os.path.exists(provided_path):
            return provided_path
        else:
            raise FileNotFoundError(f"Provided DB path not found: {provided_path}")
    for p in COMMON_LOCATIONS:
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError('Could not locate mangofy.db in common locations. Provide --db PATH')


def inspect(db_path):
    print(f"Inspecting DB: {db_path}\n")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # List tables
    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY type, name")
    items = cur.fetchall()
    tables = [r['name'] for r in items if r['type'] == 'table']

    print("Tables found:")
    for t in tables:
        print(f" - {t}")
    print('')

    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) as cnt FROM {t}")
            cnt = cur.fetchone()['cnt']
        except Exception as e:
            cnt = f"error: {e}"
        print(f"Table: {t}    Rows: {cnt}")
        # Sample rows
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 5")
            rows = [dict(r) for r in cur.fetchall()]
            if rows:
                print(json.dumps(rows, indent=2, ensure_ascii=False))
            else:
                print("  (no rows)")
        except Exception as e:
            print(f"  Could not sample rows: {e}")
        print('')

    # Show schema for all tables
    print("Full schema snippet:")
    for row in items:
        print(f"-- {row['type']}: {row['name']}")
        if row['sql']:
            print(row['sql'])
        print('')

    conn.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--db', help='Path to mangofy.db')
    args = p.parse_args()
    try:
        db = find_db(args.db)
    except FileNotFoundError as e:
        print(e)
        sys.exit(2)
    inspect(db)
