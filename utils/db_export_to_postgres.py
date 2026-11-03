import os
import sys
import argparse
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from models import db
from models.mess import Mess
from models.user import User
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit
from models.audit_log import AuditLog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def migrate_sqlite_to_postgres(sqlite_path, postgres_url):
    """
    Safely export records from local SQLite to target PostgreSQL database.
    Does NOT modify or delete the local SQLite database.
    """
    if not os.path.exists(sqlite_path):
        print(f"Error: Local SQLite database not found at {sqlite_path}")
        return False

    clean_pg_url = postgres_url.strip()
    if clean_pg_url.startswith("postgres://"):
        clean_pg_url = clean_pg_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif clean_pg_url.startswith("postgresql://"):
        clean_pg_url = clean_pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    print(f"Connecting to source SQLite: {sqlite_path}")
    print(f"Connecting to target PostgreSQL database...")

    # 1. Read source data using a dedicated SQLite session
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    SqliteSession = sessionmaker(bind=sqlite_engine)
    src_session = SqliteSession()

    # 2. Connect to target PostgreSQL
    pg_engine = create_engine(clean_pg_url, pool_pre_ping=True)
    PgSession = sessionmaker(bind=pg_engine)
    dst_session = PgSession()

    try:
        # Ensure target tables exist
        print("Ensuring target schema tables are initialized...")
        db.metadata.create_all(bind=pg_engine)

        # Read tables from SQLite
        messes = src_session.query(Mess).all()
        users = src_session.query(User).all()
        members = src_session.query(Member).all()
        meals = src_session.query(Meal).all()
        bazars = src_session.query(Bazar).all()
        deposits = src_session.query(Deposit).all()
        audit_logs = src_session.query(AuditLog).all()

        print(f"Source data found:")
        print(f" - Messes: {len(messes)}")
        print(f" - Users: {len(users)}")
        print(f" - Members: {len(members)}")
        print(f" - Meals: {len(meals)}")
        print(f" - Bazars: {len(bazars)}")
        print(f" - Deposits: {len(deposits)}")
        print(f" - Audit Logs: {len(audit_logs)}")

        # Insert Messes
        for m in messes:
            if not dst_session.get(Mess, m.id):
                dst_session.add(Mess(
                    id=m.id, name=m.name, manager_name=m.manager_name,
                    target_meal_rate=m.target_meal_rate, status=m.status, created_at=m.created_at
                ))
        dst_session.flush()

        # Insert Users
        for u in users:
            if not dst_session.get(User, u.id):
                dst_session.add(User(
                    id=u.id, mess_id=u.mess_id, username=u.username,
                    password_hash=u.password_hash, manager_name=u.manager_name,
                    role=u.role, created_at=u.created_at
                ))
        dst_session.flush()

        # Insert Members
        for mem in members:
            if not dst_session.get(Member, mem.id):
                dst_session.add(Member(
                    id=mem.id, mess_id=mem.mess_id, name=mem.name,
                    phone=mem.phone, status=mem.status, joining_date=mem.joining_date,
                    created_at=mem.created_at
                ))
        dst_session.flush()

        # Insert Meals
        for ml in meals:
            if not dst_session.get(Meal, ml.id):
                dst_session.add(Meal(
                    id=ml.id, mess_id=ml.mess_id, member_id=ml.member_id,
                    date=ml.date, meal_type=ml.meal_type, taken=ml.taken
                ))
        dst_session.flush()

        # Insert Bazars
        for b in bazars:
            if not dst_session.get(Bazar, b.id):
                dst_session.add(Bazar(
                    id=b.id, mess_id=b.mess_id, member_id=b.member_id,
                    date=b.date, amount=b.amount, description=b.description,
                    category=getattr(b, "category", "Groceries")
                ))
        dst_session.flush()

        # Insert Deposits
        for d in deposits:
            if not dst_session.get(Deposit, d.id):
                dst_session.add(Deposit(
                    id=d.id, mess_id=d.mess_id, member_id=d.member_id,
                    date=d.date, amount=d.amount, notes=d.notes,
                    payment_method=getattr(d, "payment_method", "Cash")
                ))
        dst_session.flush()

        # Insert Audit Logs
        for a in audit_logs:
            if not dst_session.get(AuditLog, a.id):
                dst_session.add(AuditLog(
                    id=a.id, admin_id=a.admin_id, admin_username=a.admin_username,
                    action=a.action, target_type=a.target_type, target_id=a.target_id,
                    target_name=a.target_name, details=a.details, ip_address=a.ip_address,
                    created_at=a.created_at
                ))
        dst_session.flush()

        # Update PostgreSQL primary key auto-increment sequences
        table_names = ["mess", "user", "member", "meal", "bazar", "deposit", "audit_log"]
        print("Updating PostgreSQL sequence counters...")
        for tbl in table_names:
            try:
                dst_session.execute(text(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), coalesce(max(id),0) + 1, false) FROM \"{tbl}\";"))
            except Exception as seq_err:
                print(f"Sequence update note for {tbl}: {seq_err}")

        dst_session.commit()
        print("Success: All local SQLite data was successfully exported to PostgreSQL!")
        return True

    except Exception as exc:
        dst_session.rollback()
        print(f"Error during migration: {exc}")
        return False
    finally:
        src_session.close()
        dst_session.close()


def main():
    parser = argparse.ArgumentParser(description="Export local SQLite MessMate database to production PostgreSQL.")
    parser.add_argument("--target-url", required=True, help="PostgreSQL connection URL (e.g. postgresql://user:pass@host/db)")
    parser.add_argument("--sqlite-path", default=os.path.join(PROJECT_ROOT, "instance", "messmate.db"),
                        help="Path to local SQLite file (default: instance/messmate.db)")

    args = parser.parse_args()
    migrate_sqlite_to_postgres(args.sqlite_path, args.target_url)


if __name__ == "__main__":
    main()
