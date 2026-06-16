"""
Pepper EMS / Suitboard Riveting – Web App
Flask backend

Run:
    pip install flask pymysql python-dotenv
    python app.py

Config:
    config.ini  -> DB, table names, queries, CSV settings
    .env        -> optional DB overrides
"""

import os, csv, datetime, configparser
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
import pymysql, pymysql.cursors

# ─────────────────────────────────────────────
# PATHS & CONFIG
# ─────────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")
load_dotenv(os.path.join(BASE_DIR, ".env"))

def _load_ini(path):
    cfg = configparser.RawConfigParser()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    cfg.read(path, encoding="utf-8")
    return cfg

_CFG = _load_ini(CONFIG_FILE)

def _tables():
    return dict(_CFG["tables"])

def _query(name):
    raw = _CFG.get("queries", name)
    raw = "\n".join(l.strip() for l in raw.strip().splitlines())
    return raw.format(**_tables())

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

DB_HOST = os.getenv("DB_HOST") or _CFG.get("database", "host",     fallback="192.168.2.5")
# DB_PORT = int(os.getenv("DB_PORT") or _CFG.get("database", "port", fallback="3306"))
DB_USER = os.getenv("DB_USER") or _CFG.get("database", "user",     fallback="labeling")
DB_PASS = os.getenv("DB_PASSWORD") or _CFG.get("database", "password", fallback="labeling")

def get_conn():
    return pymysql.connect(
        host=DB_HOST,  user=DB_USER, password=DB_PASS,
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
    )#port=DB_PORT,

def _dt_to_str(row):
    for k, v in row.items():
        if isinstance(v, (datetime.datetime, datetime.date)):
            row[k] = str(v)
    return row

# ─────────────────────────────────────────────
# DB QUERIES
# ─────────────────────────────────────────────

def check_operator(emp_num):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("check_operator"), (emp_num,))
            return cur.fetchone() is not None

def fetch_suit_sizes():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("fetch_suit_sizes"))
            return [r["suitboard_size"] for r in cur.fetchall()]

def serial_exists_in_main(serial):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("serial_exists_in_main"), (serial,))
            return cur.fetchone() is not None

def fetch_po_num(serial):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("fetch_po_num"), (serial,))
            row = cur.fetchone()
            return row["po_num"] if row and row.get("po_num") else ""

def get_riveting_records(limit=200):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("get_riveting_records"), (limit,))
            return [_dt_to_str(r) for r in cur.fetchall()]

def insert_riveting_record(record):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_query("insert_riveting_record"), record)
        conn.commit()

# ─────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────

CSV_ENABLED  = _CFG.getboolean("csv", "enabled",     fallback=True)
CSV_FOLDER   = _CFG.get("csv", "save_folder",        fallback="./exports")
CSV_FILENAME = _CFG.get("csv", "filename",            fallback="suitboard_riveting_{date}.csv")
CSV_HEADERS  = [h.strip() for h in _CFG.get(
    "csv", "headers",
    fallback="serial_num,po_num,operator_en,shift,date_time,suit_size,remarks,status"
).split(",")]

def save_to_csv(record):
    if not CSV_ENABLED:
        return
    try:
        folder = Path(CSV_FOLDER)
        folder.mkdir(parents=True, exist_ok=True)
        now = datetime.datetime.now()
        filename = CSV_FILENAME \
            .replace("{date}",  now.strftime("%Y-%m-%d")) \
            .replace("{month}", now.strftime("%Y-%m")) \
            .replace("{year}",  now.strftime("%Y"))
        filepath = folder / filename
        file_exists = filepath.exists()
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)
    except Exception as e:
        print(f"[CSV] Failed to save: {e}")

# ─────────────────────────────────────────────
# FLASK
# ─────────────────────────────────────────────

app = Flask(__name__, static_folder="static", template_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ── Login ──────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data    = request.get_json()
    emp_num = (data.get("employee_num") or "").strip().upper()
    if not emp_num:
        return jsonify({"ok": False, "error": "Employee number is required."}), 400
    try:
        found = check_operator(emp_num)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Database error: {e}"}), 500
    if not found:
        return jsonify({"ok": False, "error": f"Employee '{emp_num}' not found in database."}), 404
    return jsonify({"ok": True, "employee_num": emp_num})

# ── Suit sizes ─────────────────────────────────

@app.route("/api/suit-sizes", methods=["GET"])
def api_suit_sizes():
    try:
        sizes = fetch_suit_sizes()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "sizes": []}), 500
    return jsonify({"ok": True, "sizes": sizes})

# ── Check serial ───────────────────────────────

@app.route("/api/check-serial", methods=["POST"])
def api_check_serial():
    data   = request.get_json()
    serial = (data.get("serial_num") or "").strip()
    if not serial:
        return jsonify({"ok": False, "error": "Serial number is required."}), 400
    try:
        found = serial_exists_in_main(serial)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Database error: {e}"}), 500
    if not found:
        return jsonify({"ok": False, "error": f"Serial '{serial}' not found in suitboard_main."}), 404
    return jsonify({"ok": True})

# ── Submit record ──────────────────────────────

@app.route("/api/submit", methods=["POST"])
def api_submit():
    data     = request.get_json()
    serial   = (data.get("serial_num")  or "").strip()
    size     = (data.get("suit_size")   or "").strip()
    operator = (data.get("operator_en") or "").strip()
    shift    = (data.get("shift")       or "").strip()

    if not serial:
        return jsonify({"ok": False, "error": "Serial number is required."}), 400
    if not operator:
        return jsonify({"ok": False, "error": "Not logged in."}), 401
    if not size:
        return jsonify({"ok": False, "error": "Please select a suit size."}), 400

    try:
        if not serial_exists_in_main(serial):
            return jsonify({"ok": False, "error": f"Serial '{serial}' not found in suitboard_main."}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": f"DB error: {e}"}), 500

    po_num   = ""
    try:
        po_num = fetch_po_num(serial)
    except Exception:
        pass

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record  = {
        "serial_num":  serial,
        "po_num":      po_num,
        "operator_en": operator,
        "shift":       shift,
        "date_time":   now_str,
        "suit_size":   size,
        "remarks":     "",
        "status":      "1",
    }

    try:
        insert_riveting_record(record)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to save record: {e}"}), 500

    save_to_csv(record)

    return jsonify({"ok": True, "po_num": po_num, "date_time": now_str})

# ── Records ────────────────────────────────────

@app.route("/api/records", methods=["GET"])
def api_records():
    limit = int(request.args.get("limit", 200))
    try:
        rows = get_riveting_records(limit)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "records": rows})

# ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5080)
