-- Postgres schema for Wacky Packages Vault (public web deployment).
-- Re-apply manually (psql $DATABASE_URL -f schema.sql) after future column
-- additions, using ADD COLUMN IF NOT EXISTS -- this is not auto-run by the
-- app at request time.

CREATE TABLE IF NOT EXISTS cards (
    id SERIAL PRIMARY KEY,
    series INTEGER NOT NULL,
    sticker_number INTEGER NOT NULL,
    sticker_name TEXT NOT NULL,
    owned INTEGER NOT NULL DEFAULT 0,
    estimated_value REAL,
    notes TEXT,
    back_color TEXT,
    image_filename TEXT,
    image TEXT,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    value TEXT,
    order_date TEXT
);

CREATE TABLE IF NOT EXISTS series_puzzle_pieces (
    id SERIAL PRIMARY KEY,
    series INTEGER NOT NULL,
    piece_number INTEGER NOT NULL,
    owned INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    UNIQUE(series, piece_number)
);
