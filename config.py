import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Security: prefer environment secret key; use fallback for local development
    SECRET_KEY = os.environ.get("SECRET_KEY", "messmate-secure-dev-key-change-in-production")

    # Database: SQLite by default, configurable for PostgreSQL / MySQL in production
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or ("sqlite:///" + os.path.join(BASE_DIR, "instance", "messmate.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session protection
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production" or os.environ.get("SESSION_SECURE") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # App Branding & Defaults
    APP_NAME = "MessMate"
    CURRENCY_SYMBOL = "৳"
