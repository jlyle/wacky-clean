from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import re, csv, io, os, secrets
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
)

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

BACK_COLOR_OPTIONS = ["white", "tan", "red ludlow", "black ludlow", "cloth"]
PUZZLE_PIECES_PER_SERIES = 9

SERIES1_MAP = {
    1: {"title": "6 Up", "image": "1st_series_01_6up.jpg"},
    3: {"title": "Breadcrust", "image": "1st_series_03_breadcrust.jpg"},
    4: {"title": "Camals", "image": "1st_series_04_camals.jpg"},
    5: {"title": "Chock", "image": "1st_series_05_chock.jpg"},
    6: {"title": "Cover Ghoul", "image": "1st_series_06_coverghoul.jpg"},
    7: {"title": "Crust", "image": "1st_series_07_crust.jpg"},
    8: {"title": "Dopey Whip", "image": "1st_series_08_dopey.jpg"},
    9: {"title": "Duzn't", "image": "1st_series_09_duznt.jpg"},
    10: {"title": "Fink", "image": "1st_series_10_fink.jpg"},
    11: {"title": "Gadzooka", "image": "1st_series_11_gadzooka.jpg"},
    12: {"title": "Grave Train", "image": "1st_series_12_grave.jpg"},
    13: {"title": "Horrid", "image": "1st_series_13_horrid.jpg"},
    14: {"title": "Hostage", "image": "1st_series_14_hostage.jpg"},
    15: {"title": "Jail-O", "image": "1st_series_15_jailo.jpg"},
    16: {"title": "Kook Aid", "image": "1st_series_16_kookaid.jpg"},
    17: {"title": "Lavirus", "image": "1st_series_17_lavirus.jpg"},
    18: {"title": "Liptorn", "image": "1st_series_18_liptorn.jpg"},
    19: {"title": "Maddie Boy", "image": "1st_series_19_maddie.jpg"},
    20: {"title": "Minute Lice", "image": "1st_series_20_minute.jpg"},
    21: {"title": "Mrs. Klean", "image": "1st_series_21_mrsklean.jpg"},
    22: {"title": "Mutts", "image": "1st_series_22_mutts.jpg"},
    23: {"title": "Paul Maul", "image": "1st_series_23_paulmaul.jpg"},
    24: {"title": "Pure Hex", "image": "1st_series_24_purehex.jpg"},
    25: {"title": "Quacker Oats", "image": "1st_series_25_quacker.jpg"},
    26: {"title": "Skimpy", "image": "1st_series_26_skimpy.jpg"},
    27: {"title": "Spray Nit", "image": "1st_series_27_spraynit.jpg"},
    28: {"title": "Tied", "image": "1st_series_28_tied.jpg"},
    29: {"title": "Vicejoy", "image": "1st_series_29_vicejoy.jpg"},
    30: {"title": "Weakies", "image": "1st_series_30_weakies.jpg"},
}

class PGConnection:
    """Thin wrapper so existing conn.execute(...).fetchall() call sites need no rewrite."""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        cur = self._conn.cursor()
        cur.execute(query, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return PGConnection(conn)

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_owner"):
            return "Forbidden", 403
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_is_owner():
    return {"is_owner": bool(session.get("is_owner"))}

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password") or ""
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session["is_owner"] = True
            return redirect(request.form.get("next") or url_for("index"))
        error = "Incorrect password."
    return render_template("login.html", error=error, next=request.args.get("next", ""))

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("is_owner", None)
    return redirect(request.referrer or url_for("index"))

def normalize_owned(value):
    if value is None:
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if int(value) == 1 else 0
    return 1 if str(value).strip().lower() in {"1", "true", "yes", "owned"} else 0

def format_name(name):
    name = name or ""
    name = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", name)
    return name.strip()

def display_name(series, sticker_number, sticker_name):
    if int(series) == 1:
        mapped = SERIES1_MAP.get(int(sticker_number), {}).get("title")
        if mapped:
            return mapped
    return format_name(sticker_name)

def get_image_value(row):
    if row["image_filename"]:
        return row["image_filename"]
    if row["image"]:
        return row["image"]
    if int(row["series"]) == 1:
        return SERIES1_MAP.get(int(row["sticker_number"]), {}).get("image")
    return None

def load_cards():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, series, sticker_number, sticker_name, owned, back_color, "
        "image_filename, image, duplicate_count, notes, order_date "
        "FROM cards ORDER BY series, sticker_number"
    ).fetchall()
    conn.close()
    cards = []
    for row in rows:
        try:
            dupes = max(0, int(row["duplicate_count"] or 0))
        except Exception:
            dupes = 0
        cards.append({
            "id": int(row["id"]),
            "series": int(row["series"]),
            "sticker_number": int(row["sticker_number"]),
            "name": display_name(row["series"], row["sticker_number"], row["sticker_name"]),
            "sticker_name": row["sticker_name"],
            "owned": normalize_owned(row["owned"]),
            "back_color": row["back_color"],
            "image": get_image_value(row),
            "duplicate_count": dupes,
            "notes": row["notes"] or "",
            "order_date": row["order_date"] or "",
            "code": f"S{int(row['series']):02d}-#{int(row['sticker_number'])}",
        })
    return cards

def apply_card_filters(cards, args):
    search = (args.get("search") or "").strip().lower()
    series_filter = (args.get("series") or "").strip()
    ownership_filter = (args.get("ownership") or "").strip().lower()
    back_color_filter = (args.get("back_color") or "").strip().lower()
    sort_by = (args.get("sort") or "series_number").strip().lower()
    missing_only = (args.get("missing_only") or "").strip().lower() in {"1","true","on","yes"}
    duplicates_only = (args.get("duplicates_only") or "").strip().lower() in {"1","true","on","yes"}
    filtered = []
    for c in cards:
        if series_filter:
            try:
                if c["series"] != int(series_filter):
                    continue
            except ValueError:
                pass
        if ownership_filter == "owned" and c["owned"] != 1:
            continue
        if ownership_filter == "missing" and c["owned"] == 1:
            continue
        if missing_only and c["owned"] == 1:
            continue
        if duplicates_only and c["duplicate_count"] <= 0:
            continue
        if back_color_filter and (c["back_color"] or "").strip().lower() != back_color_filter:
            continue
        if search:
            blob = " ".join([c["name"], c["sticker_name"] or "", str(c["series"]), str(c["sticker_number"]), c["code"], c["back_color"] or "", str(c["duplicate_count"]), c["notes"] or ""]).lower()
            if search not in blob:
                continue
        filtered.append(c)
    if sort_by == "name":
        filtered.sort(key=lambda x: x["name"].lower())
    elif sort_by == "duplicates":
        filtered.sort(key=lambda x: (-x["duplicate_count"], x["series"], x["sticker_number"]))
    else:
        filtered.sort(key=lambda x: (x["series"], x["sticker_number"]))
    return filtered

def card_stats(cards):
    total_cards = len(cards)
    owned_total = sum(1 for c in cards if c["owned"] == 1)
    duplicate_total = sum(c["duplicate_count"] for c in cards)
    completion_pct = round((owned_total / total_cards) * 100, 1) if total_cards else 0
    series_progress = []
    for s in range(1, 17):
        subset = [c for c in cards if c["series"] == s]
        total = len(subset)
        owned = sum(1 for c in subset if c["owned"] == 1)
        percent = round((owned / total) * 100, 1) if total else 0
        series_progress.append({"series": s, "total": total, "owned": owned, "percent": percent})
    return total_cards, owned_total, duplicate_total, completion_pct, series_progress

def load_puzzles():
    conn = get_db()
    rows = conn.execute("SELECT series, piece_number, owned, duplicate_count, notes FROM series_puzzle_pieces ORDER BY series, piece_number").fetchall()
    conn.close()
    grouped = {}
    for s in range(1, 17):
        grouped[s] = {"series": s, "pieces": [], "owned_count": 0, "total": PUZZLE_PIECES_PER_SERIES, "duplicate_total": 0}
    for row in rows:
        try:
            dupes = max(0, int(row["duplicate_count"] or 0))
        except Exception:
            dupes = 0
        owned = normalize_owned(row["owned"])
        piece = {"series": int(row["series"]), "piece_number": int(row["piece_number"]), "owned": owned, "duplicate_count": dupes, "notes": row["notes"] or ""}
        grouped[piece["series"]]["pieces"].append(piece)
        if owned == 1:
            grouped[piece["series"]]["owned_count"] += 1
        grouped[piece["series"]]["duplicate_total"] += dupes
    return [grouped[s] for s in range(1, 17)]

@app.route("/")
def index():
    cards = load_cards()
    filtered = apply_card_filters(cards, request.args)
    total_cards, owned_total, duplicate_total, completion_pct, series_progress = card_stats(cards)
    view_mode = (request.args.get("view") or "gallery").strip().lower()
    if view_mode not in ("gallery", "spreadsheet"):
        view_mode = "gallery"
    return render_template("index.html", cards=filtered, total_cards=total_cards, owned_total=owned_total, duplicate_total=duplicate_total, completion_pct=completion_pct, series_progress=series_progress, search=request.args.get("search", ""), series_filter=request.args.get("series", ""), ownership_filter=request.args.get("ownership", ""), back_color_filter=request.args.get("back_color", ""), sort_by=request.args.get("sort", "series_number"), view_mode=view_mode, missing_only=(request.args.get("missing_only") or "").strip().lower() in {"1","true","on","yes"}, duplicates_only=(request.args.get("duplicates_only") or "").strip().lower() in {"1","true","on","yes"}, back_color_options=BACK_COLOR_OPTIONS)

@app.route("/puzzles")
def puzzles():
    grouped = load_puzzles()
    total_pieces = sum(s["total"] for s in grouped)
    owned_pieces = sum(s["owned_count"] for s in grouped)
    duplicate_total = sum(s["duplicate_total"] for s in grouped)
    percent = round((owned_pieces / total_pieces) * 100, 1) if total_pieces else 0
    return render_template("puzzles.html", puzzle_series=grouped, total_pieces=total_pieces, owned_pieces=owned_pieces, duplicate_total=duplicate_total, percent=percent)

@app.route("/update_puzzle_piece/<int:series>/<int:piece_number>", methods=["POST"])
@login_required
def update_puzzle_piece(series, piece_number):
    owned = 1 if request.form.get("owned") == "1" else 0
    notes = (request.form.get("notes") or "").strip()
    raw_dup = (request.form.get("duplicate_count") or "0").strip()
    try:
        duplicate_count = max(0, int(raw_dup))
    except ValueError:
        duplicate_count = 0
    conn = get_db()
    conn.execute("UPDATE series_puzzle_pieces SET owned = %s, duplicate_count = %s, notes = %s WHERE series = %s AND piece_number = %s", (owned, duplicate_count, notes, series, piece_number))
    conn.commit()
    conn.close()
    flash(f"Series {series} puzzle piece {piece_number} updated.")
    return redirect(request.form.get("next") or request.referrer or url_for("puzzles"))

@app.route("/card/<int:card_id>")
def card_detail(card_id):
    cards = load_cards()
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        return "Card not found", 404
    return render_template("card_detail.html", card=card)

@app.route("/update_notes/<int:card_id>", methods=["POST"])
@login_required
def update_notes(card_id):
    notes = (request.form.get("notes") or "").strip()
    conn = get_db()
    conn.execute("UPDATE cards SET notes = %s WHERE id = %s", (notes, card_id))
    conn.commit()
    conn.close()
    flash("Notes updated.")
    return redirect(request.form.get("next") or request.referrer or url_for("card_detail", card_id=card_id))

@app.route("/mark_owned/<int:card_id>", methods=["POST"])
@login_required
def mark_owned(card_id):
    conn = get_db()
    conn.execute("UPDATE cards SET owned = 1 WHERE id = %s", (card_id,))
    conn.commit()
    conn.close()
    flash("Card marked as owned.")
    return redirect(request.form.get("next") or request.referrer or url_for("index"))

@app.route("/mark_missing/<int:card_id>", methods=["POST"])
@login_required
def mark_missing(card_id):
    conn = get_db()
    conn.execute("UPDATE cards SET owned = 0, duplicate_count = 0 WHERE id = %s", (card_id,))
    conn.commit()
    conn.close()
    flash("Card marked as missing.")
    return redirect(request.form.get("next") or request.referrer or url_for("index"))

@app.route("/update_duplicates/<int:card_id>", methods=["POST"])
@login_required
def update_duplicates(card_id):
    raw = (request.form.get("duplicate_count") or "0").strip()
    try:
        value = max(0, int(raw))
    except ValueError:
        value = 0
    conn = get_db()
    if value > 0:
        conn.execute("UPDATE cards SET duplicate_count = %s, owned = 1 WHERE id = %s", (value, card_id))
    else:
        conn.execute("UPDATE cards SET duplicate_count = 0 WHERE id = %s", (card_id,))
    conn.commit()
    conn.close()
    flash("Duplicate count updated.")
    return redirect(request.form.get("next") or request.referrer or url_for("index"))

@app.route("/export/csv")
def export_csv():
    cards = load_cards()
    filtered = apply_card_filters(cards, request.args)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Series", "Number", "Name", "Status", "Duplicates", "Back Color", "Code", "Notes", "Date Ordered"])
    for c in filtered:
        writer.writerow([
            c["series"],
            c["sticker_number"],
            c["name"],
            "Owned" if c["owned"] == 1 else "Missing",
            c["duplicate_count"],
            c["back_color"] or "",
            c["code"],
            c["notes"] or "",
            c["order_date"] or "",
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=wacky-packages.csv"},
    )

@app.route("/export/txt")
def export_txt():
    cards = load_cards()
    filtered = apply_card_filters(cards, request.args)
    lines = [f"Wacky Packages - s{c['series']} #{c['sticker_number']} {c['name']}" for c in filtered]
    return Response(
        "\n".join(lines) + "\n",
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wacky-packages.txt"},
    )

@app.route("/export/duplicates")
def export_duplicates():
    cards = load_cards()
    filtered = [c for c in cards if c["duplicate_count"] > 0]
    filtered.sort(key=lambda c: (c["series"], c["sticker_number"]))
    name_width = max((len(c["name"]) for c in filtered), default=0)
    lines = []
    current_series = None
    for c in filtered:
        if c["series"] != current_series:
            if current_series is not None:
                lines.append("")
            current_series = c["series"]
            lines.append(f"Series {c['series']}")
            lines.append("")
        lines.append(f"{c['name'].ljust(name_width)}   {c['duplicate_count']}")
    return Response(
        "\n".join(lines) + ("\n" if lines else ""),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wacky-packages-duplicates.txt"},
    )

@app.route("/export/owned")
def export_owned():
    cards = load_cards()
    series_total = {}
    series_owned = {}
    for c in cards:
        series_total[c["series"]] = series_total.get(c["series"], 0) + 1
        if c["owned"] == 1:
            series_owned[c["series"]] = series_owned.get(c["series"], 0) + 1
    cards = [c for c in cards if c["owned"] == 1]
    cards.sort(key=lambda c: (c["series"], c["sticker_number"]))
    name_width = max((len(c["name"]) for c in cards), default=0)
    num_width = max((len(str(c["sticker_number"])) for c in cards), default=0)
    lines = []
    current_series = None
    for c in cards:
        if c["series"] != current_series:
            if current_series is not None:
                lines.append("")
            current_series = c["series"]
            owned_n = series_owned.get(c["series"], 0)
            total_n = series_total.get(c["series"], 0)
            progress = f"{owned_n}/{total_n}"
            if total_n and owned_n == total_n:
                progress += "     complete series"
            lines.append(f"Series {c['series']}     {progress}")
            lines.append("")
            lines.append("")
        back = c["back_color"] or ""
        num = f"#{c['sticker_number']}".ljust(num_width + 1)
        lines.append(f"{num}  {c['name'].ljust(name_width)}   {back}")
    return Response(
        "\n".join(lines) + ("\n" if lines else ""),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wacky-packages-owned.txt"},
    )

@app.route("/export/missing")
def export_missing():
    cards = load_cards()
    cards = [c for c in cards if c["owned"] != 1]
    cards.sort(key=lambda c: (c["series"], c["sticker_number"]))
    lines = []
    current_series = None
    for c in cards:
        if c["series"] != current_series:
            if current_series is not None:
                lines.append("")
            current_series = c["series"]
            lines.append(f"Series {c['series']}")
            lines.append("")
        lines.append(f"#{c['sticker_number']} - {c['name']}")
    return Response(
        "\n".join(lines) + ("\n" if lines else ""),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wacky-packages-missing.txt"},
    )

@app.route("/export/orders")
def export_orders():
    date_from = (request.args.get("from") or "").strip()
    date_to = (request.args.get("to") or "").strip()
    cards = load_cards()
    cards = [c for c in cards if c["order_date"]]
    if date_from:
        cards = [c for c in cards if c["order_date"] >= date_from]
    if date_to:
        cards = [c for c in cards if c["order_date"] <= date_to]
    cards.sort(key=lambda c: (c["series"], c["name"], c["order_date"]))
    name_width = max((len(c["name"]) for c in cards), default=0)
    lines = []
    current_series = None
    for c in cards:
        if c["series"] != current_series:
            if current_series is not None:
                lines.append("")
            current_series = c["series"]
            lines.append(f"Series {c['series']}")
            lines.append("")
        lines.append(f"{c['name'].ljust(name_width)}   {c['order_date']}")
    return Response(
        "\n".join(lines) + ("\n" if lines else ""),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wacky-packages-orders.txt"},
    )

@app.route("/update_back_color/<int:card_id>", methods=["POST"])
@login_required
def update_back_color(card_id):
    value = request.form.get("back_color") or None
    conn = get_db()
    conn.execute("UPDATE cards SET back_color = %s WHERE id = %s", (value, card_id))
    conn.commit()
    conn.close()
    flash("Back color updated.")
    return redirect(request.form.get("next") or request.referrer or url_for("index"))

@app.route("/update_order_date/<int:card_id>", methods=["POST"])
@login_required
def update_order_date(card_id):
    value = request.form.get("order_date") or None
    conn = get_db()
    conn.execute("UPDATE cards SET order_date = %s WHERE id = %s", (value, card_id))
    conn.commit()
    conn.close()
    flash("Order date updated.")
    return redirect(request.form.get("next") or request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
