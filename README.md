# Wacky Packages Vault

A self-hosted Flask app for tracking a personal collection of original-series
Wacky Packages stickers: 488 cards across 16 series, plus the 16-series jigsaw
puzzle-back set (9 pieces per series, 144 pieces total). Data lives in a
single SQLite file (`wacky_packages.db`) that's tracked in this repo.

## Running it

```bash
./run.sh
```

This creates a venv, installs Flask, and starts the app at
`http://localhost:5001`.

## Inventory

Each card tracks:

- **Owned / Missing** status
- **Duplicate count** (also flips the card to owned when set above 0)
- **Back color** (white, tan, red ludlow, black ludlow, cloth)
- **Notes** (free text, editable per card)

Cards are viewable in two layouts:

- **Gallery** — image-first cards with inline forms for back color,
  duplicate count, and owned/missing toggling.
- **Spreadsheet** — dense table with the same fields, better for bulk
  scanning or editing.

A **card detail** page (click a card name/Details) shows the full record and
a larger notes editor.

## Filtering & search

The card list can be filtered and sorted by:

- Free-text search (name, series, sticker number, back color, notes, code)
- Series (1–16)
- Ownership (owned / missing)
- Back color
- "Missing only" / "Duplicates only" checkboxes
- Sort by series+number, name, or duplicate count

## Puzzle tracker

A separate `/puzzles` page tracks the 16-series puzzle-back set independently
from the main cards, with the same owned/missing toggle, duplicate count, and
notes per piece, plus per-series and overall completion stats.

## Statistics

The home page header shows running totals:

- Cards in vault (488)
- Owned count
- Completion percentage
- Total duplicate count

A sidebar shows per-series progress bars (owned/total and %) for all 16
series, and the puzzle tracker shows the same for puzzle pieces.

## Reporting / exports

From the card list, respecting whatever filters are currently applied:

- **Save CSV** — full record dump (series, number, name, status, duplicates,
  back color, code, notes)
- **Save TXT** — plain list of owned/filtered cards, one per line
- **Save PDF** — browser print of the current view

Unfiltered, whole-collection reports:

- **Save Dupes TXT** — every card with duplicates, grouped by series
- **Save Owned TXT** — every owned card, grouped by series, with
  `owned/total` progress and a "complete series" marker when a series is
  fully collected

## Tech

- Flask + SQLite (stdlib `sqlite3`, no ORM)
- Server-rendered Jinja templates, no JS framework
- Card images in `static/cards/`
