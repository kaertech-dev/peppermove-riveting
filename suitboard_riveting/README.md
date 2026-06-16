# Pepper EMS – Packaging Station (Web App)

## Files
```
packaging_webapp/
├── app.py           ← Flask backend (REST API)
├── config.ini       ← DB credentials, table names, queries, CSV settings
├── requirements.txt ← Python dependencies
├── .env             ← (optional) override DB credentials per-machine
├── exports/         ← CSV files saved here (auto-created)
└── static/
    └── index.html   ← Frontend UI
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Edit config.ini — set your DB host, credentials, table names

# 3. Run
python app.py
```

Then open your browser at: **http://localhost:5000**

To expose on your local network (e.g. for shop-floor tablets):
```bash
python app.py
# Already binds to 0.0.0.0:5000 — access via http://<your-pc-ip>:5000
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/login` | Validate employee number |
| POST | `/api/scan`  | Process serial, save to DB + CSV |
| GET  | `/api/records?limit=N` | Fetch recent packaging records |

## CSV Output

Saved to `exports/ems_packaging_YYYY-MM-DD.csv` (one file per day).  
Configure folder, filename pattern, and columns in `config.ini [csv]`.

## .env (optional)

Create a `.env` file next to `app.py` to override DB credentials per machine:
```
DB_HOST=192.168.1.38
DB_PORT=3306
DB_USER=labeling
DB_PASSWORD=labeling
```
