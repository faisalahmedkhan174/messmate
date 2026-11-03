import os
import sys
import argparse
import getpass
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from models import db
from models.user import User
from models.mess import Mess
from models.audit_log import AuditLog


def list_users():
    """Display all registered users, their mess, and their role."""
    users = User.query.order_by(User.id.asc()).all()
    if not users:
        print("No users found.")
        return

    print("\n" + "=" * 70)
    print(f"{'ID':<5} {'Username':<18} {'Role':<12} {'Mess':<20} {'Manager Name'}")
    print("-" * 70)
    for u in users:
        mess_name = u.mess.name if u.mess else "N/A"
        print(f"{u.id:<5} {u.username:<18} {u.role:<12} {mess_name:<20} {u.manager_name}")
    print("=" * 70 + "\n")


def promote_user(username=None, user_id=None):
    """Promote an existing user to Creator / Super Admin."""
    if user_id:
        user = db.session.get(User, user_id)
        if not user:
            print(f"Error: User ID {user_id} not found.")
            return False
        users = [user]
    elif username:
        users = User.query.filter_by(username=username).all()
        if not users:
            print(f"Error: No users found with username '{username}'.")
            return False
    else:
        print("Error: Must provide either --username or --id.")
        return False

    promoted_count = 0
    for user in users:
        if user.role == "Creator":
            print(f"Notice: User #{user.id} '{user.username}' is already a Creator.")
            continue

        old_role = user.role
        user.role = "Creator"
        mess_name = user.mess.name if user.mess else "N/A"

        log = AuditLog(
            admin_id=user.id,
            admin_username="CLI_SETUP",
            action="PROMOTE_CREATOR",
            target_type="User",
            target_id=user.id,
            target_name=user.username,
            details=f"User #{user.id} '{user.username}' promoted from '{old_role}' to 'Creator' via CLI.",
            ip_address="127.0.0.1",
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        promoted_count += 1
        print(f"Success: User #{user.id} '{user.username}' (Mess: {mess_name}) promoted to Creator role!")

    if promoted_count > 0:
        db.session.commit()
    return True


def demote_user(username=None, user_id=None):
    """Demote a user from Creator to Manager (ensuring at least 1 Creator remains)."""
    if user_id:
        user = db.session.get(User, user_id)
        if not user:
            print(f"Error: User ID {user_id} not found.")
            return False
    elif username:
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Error: User '{username}' not found.")
            return False
    else:
        print("Error: Must provide either --username or --id.")
        return False

    if user.role != "Creator":
        print(f"Notice: User '{user.username}' is not a Creator (Current role: '{user.role}').")
        return False

    creator_count = User.query.filter_by(role="Creator").count()
    if creator_count <= 1:
        print("Error: Cannot demote the only Creator account in the system.")
        return False

    user.role = "Manager"
    log = AuditLog(
        admin_id=user.id,
        admin_username="CLI_SETUP",
        action="DEMOTE_CREATOR",
        target_type="User",
        target_id=user.id,
        target_name=user.username,
        details=f"User #{user.id} '{user.username}' demoted to 'Manager' via CLI.",
        ip_address="127.0.0.1",
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()
    print(f"Success: User #{user.id} '{user.username}' demoted to Manager role.")
    return True


def create_creator(mess_name, username, manager_name, password=None):
    """Create a new mess and an initial Creator account."""
    clean_user = username.strip()
    clean_mess = mess_name.strip()
    clean_name = manager_name.strip()

    if not clean_user or not clean_mess or not clean_name:
        print("Error: Mess name, username, and manager name are all required.")
        return False

    if not password:
        password = getpass.getpass("Enter password for new Creator account: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.")
            return False

    if len(password) < 4:
        print("Error: Password must be at least 4 characters long.")
        return False

    # Check if mess already exists
    mess = Mess.query.filter(db.func.lower(Mess.name) == clean_mess.lower()).first()
    if not mess:
        mess = Mess(name=clean_mess, manager_name=clean_name, status="Active")
        db.session.add(mess)
        db.session.flush()

    # Check if username exists in mess
    existing_user = User.query.filter_by(mess_id=mess.id, username=clean_user).first()
    if existing_user:
        print(f"Error: User '{clean_user}' already exists in mess '{mess.name}'.")
        return False

    creator = User(
        mess_id=mess.id,
        username=clean_user,
        manager_name=clean_name,
        role="Creator"
    )
    creator.set_password(password)
    db.session.add(creator)
    db.session.flush()

    log = AuditLog(
        admin_id=creator.id,
        admin_username="CLI_SETUP",
        action="CREATE_CREATOR",
        target_type="User",
        target_id=creator.id,
        target_name=creator.username,
        details=f"New Creator account '{creator.username}' created via CLI for mess '{mess.name}'.",
        ip_address="127.0.0.1",
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()
    print(f"Success: Creator account '{clean_user}' successfully created for mess '{mess.name}'!")
    return True


def main():
    parser = argparse.ArgumentParser(description="MessMate Creator / Super Admin Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    subparsers.add_parser("list", help="List all accounts, their roles, and messes")

    # promote
    promote_parser = subparsers.add_parser("promote", help="Promote an existing user to Creator")
    promote_parser.add_argument("--username", required=False, help="Username to promote")
    promote_parser.add_argument("--id", type=int, required=False, help="Specific user ID to promote")

    # demote
    demote_parser = subparsers.add_parser("demote", help="Demote a user from Creator to Manager")
    demote_parser.add_argument("--username", required=False, help="Username to demote")
    demote_parser.add_argument("--id", type=int, required=False, help="Specific user ID to demote")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new Creator account")
    create_parser.add_argument("--mess", required=True, help="Mess / Hostel name")
    create_parser.add_argument("--username", required=True, help="Desired username")
    create_parser.add_argument("--name", required=True, help="Manager / Creator display name")
    create_parser.add_argument("--password", required=False, help="Password (will prompt securely if omitted)")

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.command == "list":
            list_users()
        elif args.command == "promote":
            promote_user(username=args.username, user_id=args.id)
        elif args.command == "demote":
            demote_user(username=args.username, user_id=args.id)
        elif args.command == "create":
            create_creator(args.mess, args.username, args.name, args.password)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
