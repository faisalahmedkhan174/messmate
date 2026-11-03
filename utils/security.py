import secrets
from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app, abort
from models.mess import Mess


def login_required(view_func):
    """Ensure user and mess sessions are active before accessing protected views."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("mess_id") or not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))

        # Verify active status of mess (Creators exempt)
        if session.get("role") != "Creator":
            mess = current_mess()
            if mess and getattr(mess, "status", "Active") == "Suspended":
                session.clear()
                flash("This mess has been suspended by the administrator. Please contact support.", "danger")
                return redirect(url_for("auth.login"))

        return view_func(*args, **kwargs)
    return wrapped


def creator_required(view_func):
    """
    Ensure user is authenticated and possesses the 'Creator' role.
    Returns HTTP 403 Forbidden if user is authenticated but not a Creator.
    Redirects to login if not authenticated at all.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in with an administrator account to continue.", "warning")
            return redirect(url_for("auth.login"))

        from models import db
        from models.user import User
        user = db.session.get(User, user_id)
        if not user or not user.is_creator:
            abort(403)

        return view_func(*args, **kwargs)
    return wrapped


def current_mess():
    """Fetch the active Mess model instance strictly bound to the server-side session."""
    mess_id = session.get("mess_id")
    if not mess_id:
        return None
    from models import db
    return db.session.get(Mess, mess_id)


def current_user():
    """Fetch the active User model instance strictly bound to the server-side session."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    from models import db
    from models.user import User
    return db.session.get(User, user_id)


def generate_csrf_token():
    """Generate or retrieve the session-scoped CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf():
    """
    Validate CSRF token on modifying HTTP requests.
    Exempts GET, HEAD, OPTIONS, and when running in test mode (app.config['TESTING']).
    """
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return

    if current_app.config.get("TESTING", False):
        return

    expected_token = session.get("_csrf_token")
    if not expected_token:
        # Session has no CSRF token initialized
        abort(400, description="Missing CSRF session token.")

    # Check form data, json body, or request headers
    provided_token = (
        request.form.get("csrf_token")
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )

    if not provided_token and request.is_json:
        json_data = request.get_json(silent=True) or {}
        provided_token = json_data.get("csrf_token")

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        abort(400, description="Invalid or missing CSRF token.")
