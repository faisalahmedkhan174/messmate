import os
import shutil
import sqlite3
from datetime import datetime


def backup_database(db_path):
    """Safely back up the SQLite database file if it exists."""
    if not os.path.exists(db_path):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def apply_migrations(db_path):
    """Non-destructively apply incremental schema migrations to SQLite only if needed."""
    if not os.path.exists(db_path):
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    try:
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        # Check if migration is actually needed
        needs_migration = False

        # 1. Check mess table status column
        if "mess" in tables:
            mess_cols = [c[1] for c in cur.execute("PRAGMA table_info('mess')").fetchall()]
            if "status" not in mess_cols:
                needs_migration = True

        # 2. Check bazar table category column
        if "bazar" in tables:
            bazar_cols = [c[1] for c in cur.execute("PRAGMA table_info('bazar')").fetchall()]
            if "category" not in bazar_cols:
                needs_migration = True

        # 3. Check deposit table payment_method column
        if "deposit" in tables:
            deposit_cols = [c[1] for c in cur.execute("PRAGMA table_info('deposit')").fetchall()]
            if "payment_method" not in deposit_cols:
                needs_migration = True

        # 4. Check audit_log table
        if "audit_log" not in tables:
            needs_migration = True

        if not needs_migration:
            return

        # Migration is needed: create safety backup first
        backup_path = backup_database(db_path)
        if backup_path:
            print(f"Pre-migration backup saved to: {backup_path}")

        # 1. Add status to mess
        if "mess" in tables:
            mess_cols = [c[1] for c in cur.execute("PRAGMA table_info('mess')").fetchall()]
            if "status" not in mess_cols:
                cur.execute("ALTER TABLE mess ADD COLUMN status VARCHAR(20) DEFAULT 'Active'")

        # 2. Add category to bazar
        if "bazar" in tables:
            bazar_cols = [c[1] for c in cur.execute("PRAGMA table_info('bazar')").fetchall()]
            if "category" not in bazar_cols:
                cur.execute("ALTER TABLE bazar ADD COLUMN category VARCHAR(50) DEFAULT 'Groceries'")

        # 3. Add payment_method to deposit
        if "deposit" in tables:
            deposit_cols = [c[1] for c in cur.execute("PRAGMA table_info('deposit')").fetchall()]
            if "payment_method" not in deposit_cols:
                cur.execute("ALTER TABLE deposit ADD COLUMN payment_method VARCHAR(50) DEFAULT 'Cash'")

        # 4. Create audit_log table if not exists
        if "audit_log" not in tables:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    admin_username VARCHAR(80) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    target_type VARCHAR(50) NOT NULL,
                    target_id INTEGER,
                    target_name VARCHAR(150),
                    details VARCHAR(500),
                    ip_address VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES user (id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at)")

        # 5. Compound performance indexes
        if "meal" in tables:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meal_mess_date ON meal (mess_id, date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meal_mess_member ON meal (mess_id, member_id)")
        if "bazar" in tables:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bazar_mess_date ON bazar (mess_id, date)")
        if "deposit" in tables:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_deposit_mess_date ON deposit (mess_id, date)")

        con.commit()
    except Exception as e:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "messmate.db")
    apply_migrations(db_file)
