"""One-off migration: copy wacky_packages.db (SQLite) into Postgres (DATABASE_URL).

Run once, locally, after provisioning Neon and before the first deploy:
    DATABASE_URL=postgres://... python3 migrate_to_postgres.py

Preserves original row ids (card_detail.html links are /card/<id>), fixes
the SERIAL sequences afterward, and asserts expected row counts so a partial
or empty migration fails loudly instead of silently.
"""
import os
import sqlite3
import sys
from pathlib import Path

import psycopg2

BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "wacky_packages.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

EXPECTED_CARD_COUNT = 489
EXPECTED_PUZZLE_COUNT = 144

CARD_COLUMNS = [
    "id", "series", "sticker_number", "sticker_name", "owned",
    "estimated_value", "notes", "back_color", "image_filename", "image",
    "duplicate_count", "value", "order_date",
]
PUZZLE_COLUMNS = [
    "id", "series", "piece_number", "owned", "duplicate_count", "notes",
]


def migrate_table(sqlite_conn, pg_conn, table, columns, expected_count):
    rows = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
    if not rows:
        sys.exit(f"ERROR: no rows found in sqlite table {table!r}, aborting")

    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    with pg_conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        for row in rows:
            cur.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                tuple(row),
            )
        cur.execute(
            "SELECT setval(pg_get_serial_sequence(%s, 'id'), (SELECT MAX(id) FROM " + table + "))",
            (table,),
        )
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        actual_count = cur.fetchone()[0]

    if actual_count != expected_count:
        sys.exit(
            f"ERROR: {table} has {actual_count} rows after migration, "
            f"expected {expected_count} -- aborting, NOT committing"
        )
    print(f"{table}: migrated {actual_count} rows (expected {expected_count}) - OK")


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("ERROR: DATABASE_URL environment variable is not set")
    if not SQLITE_PATH.exists():
        sys.exit(f"ERROR: {SQLITE_PATH} not found")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = psycopg2.connect(database_url)
    try:
        with pg_conn.cursor() as cur:
            cur.execute(SCHEMA_PATH.read_text())

        migrate_table(sqlite_conn, pg_conn, "cards", CARD_COLUMNS, EXPECTED_CARD_COUNT)
        migrate_table(sqlite_conn, pg_conn, "series_puzzle_pieces", PUZZLE_COLUMNS, EXPECTED_PUZZLE_COUNT)

        pg_conn.commit()
        print("Migration committed successfully.")
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
