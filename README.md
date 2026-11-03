# MessMate — Smart Hostel & Mess Management System

A multi-mess hostel and mess management web application built with Python, Flask, SQLAlchemy, and a modern White + Sky Blue responsive design system. MessMate simplifies daily meal tracking, bazar (grocery) accounting, member deposits, and monthly financial settlements with server-side multi-mess data isolation.

---

## Key Features

- **Multi-Mess Isolation**: Secure server-side isolation ensuring users only access their own mess's data.
- **Service Layer Architecture**: Clean separation between routes, services (`MemberService`, `MealService`, `BazarService`, `DepositService`, `SettlementService`, `ReportService`), models, and utilities.
- **High-Performance Aggregations**: Optimized SQL queries eliminating N+1 query loops; scales smoothly to unlimited members (30+, 100+, 500+).
- **Daily Meal Attendance**: Touch-optimized grid with instantaneous optimistic updates, live auto-save indicators, and fast search filter.
- **Bazar & Deposit Tracking**: Flexible categorization (Groceries, Fish/Meat, Vegetables, Spices & Oil, Other), payment methods, and daily totals.
- **Live Settlement Engine**: Live running meal rate, target rate alerts, and exact per-member balances (Refund 🟢, Due 🔴, Settled ✓).
- **Bangladeshi Taka Currency**: Centralized currency formatting (`৳1,250.00`) across all templates.
- **Reporting & Exports**: Printable monthly reports, yearly trends line chart (Chart.js), and streaming CSV exports for settlement, members, bazar, and deposits.
- **Security Hardened**: Password hashing via Werkzeug, session-based CSRF protection, secure session cookies, security headers, and branded custom error pages (400, 403, 404, 500).
- **Mobile-First Responsive UI**: Tested across viewports from 320px to 1280px+ with zero horizontal overflow, 44px+ touch targets, and responsive card-table transforms.
- **Offline Assets**: Inter fonts, Bootstrap 5, Bootstrap Icons, and Chart.js vendored locally offline in `static/vendor/`.

---

## Project Structure

```
messmate/
├── app.py                      # Application factory, CSRF filter, security headers, error handlers
├── config.py                   # Environment-driven configuration (DB URI, SECRET_KEY, session flags)
├── requirements.txt            # Application dependencies
├── README.md                   # Documentation
│
├── models/                     # SQLAlchemy models with indexes and cascades
│   ├── __init__.py             # Database instance
│   ├── mess.py                 # Mess entity with target meal rate & relationships
│   ├── user.py                 # Manager credentials with secure password hashing
│   ├── member.py               # Member profiles and status
│   ├── meal.py                 # Daily meal records with unique constraints
│   ├── bazar.py                # Bazar expense entries with category support
│   └── deposit.py              # Member deposit payments with payment methods
│
├── services/                   # Business logic and database operations
│   ├── __init__.py
│   ├── member_service.py       # Member CRUD, status toggle, member summary
│   ├── meal_service.py         # Fast meal toggling and monthly matrix
│   ├── bazar_service.py        # Bazar expenses, daily sums, category breakdown
│   ├── deposit_service.py      # Deposit recording and monthly totals
│   ├── settlement_service.py   # Batch settlement calculations (no N+1 queries)
│   └── report_service.py       # Monthly/yearly statements and CSV exports
│
├── utils/                      # Utilities
│   ├── __init__.py
│   ├── currency.py             # Centralized BDT (৳) currency formatting & rounding
│   ├── dates.py                # Leap-year safe dates and month date ranges
│   ├── security.py             # CSRF protection and login enforcement
│   └── db_migrate.py           # Safe SQLite schema migration & backup tool
│
├── routes/                     # Blueprint controllers
│   ├── auth.py                 # Login, register, logout
│   ├── dashboard.py            # Overview metrics, running rate chart, settlement summary
│   ├── members.py              # Member list, search, add/edit modals
│   ├── meals.py                # High-speed daily meal grid
│   ├── bazar.py                # Bazar expense entries and daily totals
│   ├── deposits.py             # Deposit recording and history
│   ├── settlement.py           # Balance sheet and target meal rate management
│   ├── reports.py              # Monthly/yearly analytics and CSV exports
│   ├── settings.py             # Profile settings, password change, demo data, JSON backup
│   ├── about.py                # Creator & application details
│   └── helpers.py              # Backward-compatible facade for external callers
│
├── templates/                  # Jinja2 templates (White + Sky Blue design system)
│   ├── base.html               # Main layout with responsive navbar and notifications
│   ├── _month_selector.html    # Month and year navigation
│   ├── dashboard.html          # KPI cards, trend chart, daily history
│   ├── members.html            # Responsive card-table, member search
│   ├── member_details.html     # Member stats, meal breakdown, payment history
│   ├── meals.html              # High-speed meal toggle interface
│   ├── bazar.html              # Bazar entry tracking with categories
│   ├── deposits.html           # Deposit tracking with payment methods
│   ├── settlement.html         # Settlement balance sheet with status badges
│   ├── reports.html            # Printable statements and CSV exports
│   ├── settings.html           # System and profile settings
│   ├── about.html              # Faisal Ahmed Khan creator profile
│   ├── login.html              # Manager login
│   ├── register.html           # Mess account registration
│   └── errors/                 # Custom 400, 403, 404, 500 error pages
│
├── static/
│   ├── css/style.css           # Custom responsive styles and design tokens
│   ├── js/main.js              # Alert auto-dismiss, nav collapse, search filter
│   ├── creator.jpg             # Creator avatar
│   └── vendor/                 # Offline assets (Bootstrap, Icons, Chart.js, Inter)
│
├── instance/                   # SQLite database directory (auto-created)
│   └── messmate.db
│
└── tests/                      # Automated test suite
    ├── test_services.py        # Service layer unit tests
    ├── test_security_and_isolation.py # CSRF and cross-mess isolation tests
    ├── test_currency_and_calculations.py # Currency formatting & math precision tests
    └── test_responsive_html.py # Viewport, creator image, and UI label integrity tests
```

---

## Local Setup

### 1. Prerequisites
- Python 3.10+
- `pip`

### 2. Installation
```bash
git clone <repository_url>
cd messmate
pip install -r requirements.txt
```

### 3. Run Locally
```bash
python app.py
```
The application starts at **http://127.0.0.1:5000**.
The SQLite database (`instance/messmate.db`) initializes automatically with all tables and safe migration checks.

---

## Production Deployment

### 1. Environment Variables
Set the following environment variables in production:
```bash
export SECRET_KEY="your-strong-random-secret-key"
export FLASK_ENV="production"
export DATABASE_URL="postgresql://user:password@localhost:5432/messmate"  # Optional: PostgreSQL
```

### 2. WSGI Server (Gunicorn)
Run using Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

### 3. Reverse Proxy (Nginx)
Proxy requests from port 80/443 to `http://127.0.0.1:8000`. Ensure `X-Forwarded-For` and `X-Forwarded-Proto` headers are passed.

---

## Testing

Run all automated test suites:

```bash
# 1. Run full unit test suite
python -m unittest discover -s tests -p "test_*.py"

# 2. Run end-to-end integration flow test
python test_flow.py

# 3. Run unlimited members test (verifying 35+ members support)
python test_unlimited_members.py
```

---

## Creator Information

- **Creator & Developer**: Faisal Ahmed Khan
- **Department**: Electrical and Electronic Engineering (EEE), Hajee Mohammad Danesh Science and Technology University (HSTU - 25)
- **Phone**: 01923816858
- **Email**: faisalaks321@gmail.com
- **Facebook**: [facebook.com/share/19VTRi4NqG/](https://www.facebook.com/share/19VTRi4NqG/)
