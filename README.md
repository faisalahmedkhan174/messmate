# MessMate — Hostel/Mess Management System

A multi-mess hostel/mess management web app built with Flask, SQLAlchemy, and
SQLite. Any hostel/mess can register its own account; each mess's data
(members, meals, বাজার, deposits, settings) is fully isolated on the server
side.

## Stack

- Backend: Python, Flask, SQLAlchemy
- Database: SQLite (file created automatically at `instance/messmate.db`)
- Frontend: HTML, CSS, JavaScript, Bootstrap 5, Chart.js (via CDN)
- Templates: Jinja2

## Setup

```bash
pip install -r requirements.txt
```

(If your environment requires it: `pip install -r requirements.txt --break-system-packages`)

## Run

```bash
python app.py
```

The app starts on **http://127.0.0.1:5000**. The SQLite database file and
tables are created automatically on first run — no manual DB setup needed.

## First use

1. Go to `/register` and create a mess account (mess name, manager name,
   username, password).
2. Log in at `/login` using the mess name + username + password.
3. Add members under **Members**.
4. Mark daily meals under **Meals** (auto-saves on tap).
5. Log বাজার entries under **বাজার**, and deposits under **Deposits**.
6. Set a target meal rate under **Settlement** or **Settings** (optional).
7. View running/final meal rate, charts, and settlement on **Dashboard**,
   **Settlement**, and **Reports**. CSV/JSON export available from
   **Reports** and **Settings**.

Optional: **Settings → Load Demo Data** populates sample members, meals,
বাজার, and deposits for the current month so you can explore the app
immediately.

## Project structure

```
messmate/
├── app.py                 # App factory, blueprint registration, DB init
├── config.py               # Configuration (DB URI, secret key)
├── requirements.txt
├── test_flow.py             # Automated end-to-end test suite
├── instance/                 # SQLite DB file lives here (auto-created)
├── models/                    # SQLAlchemy models (Mess, User, Member, Meal, Bazar, Deposit)
├── routes/                     # Flask blueprints (auth, dashboard, members, meals,
│                                 bazar, deposits, settlement, reports, settings, helpers)
├── templates/                   # Jinja2 templates (Bootstrap 5 + Chart.js)
└── static/                       # CSS and JS
    ├── css/style.css
    └── js/main.js
```

## Testing

An automated end-to-end test suite is included and covers the full flow:
register → login → members → meals → বাজার → deposits → running/final meal
rate → settlement → editing old records and verifying recalculation →
logout/login persistence → leap-year day counts → zero-data safety →
two-mess data isolation.

```bash
python test_flow.py
```

This runs against a separate `instance/test_messmate.db` file (created and
removed automatically) so it never touches your real data.

## Notes

- Passwords are hashed with Werkzeug's `generate_password_hash`.
- Every DB query is scoped to the logged-in mess's ID from the server-side
  session — a mess ID can never be supplied or trusted from the client.
- Meal rate and settlement figures are always computed live from Meals +
  বাজার + Deposits; nothing is cached as a stale source of truth.
