import os
from datetime import datetime
from flask import Flask, session, render_template, request

from config import Config
from models import db
from utils.currency import format_bdt
from utils.security import generate_csrf_token, validate_csrf
from utils.db_migrate import apply_migrations


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    instance_dir = os.path.join(os.path.dirname(__file__), "instance")
    os.makedirs(instance_dir, exist_ok=True)

    db.init_app(app)

    # Register Blueprints
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.members import bp as members_bp
    from routes.meals import bp as meals_bp
    from routes.bazar import bp as bazar_bp
    from routes.deposits import bp as deposits_bp
    from routes.settlement import bp as settlement_bp
    from routes.reports import bp as reports_bp
    from routes.settings import bp as settings_bp
    from routes.about import bp as about_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(meals_bp)
    app.register_blueprint(bazar_bp)
    app.register_blueprint(deposits_bp)
    app.register_blueprint(settlement_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(admin_bp)

    # Template filters
    @app.template_filter("bdt")
    def bdt_filter(value):
        """Centralized Taka currency formatting filter."""
        return format_bdt(value)

    # Context processors
    @app.context_processor
    def inject_globals():
        return {
            "session_mess_name": session.get("mess_name"),
            "session_manager_name": session.get("manager_name"),
            "session_role": session.get("role", "Manager"),
            "is_creator": session.get("is_creator", False),
            "csrf_token": generate_csrf_token,
            "current_year": datetime.now().year,
        }

    # Security: CSRF check on modifying requests
    @app.before_request
    def check_csrf():
        validate_csrf()

    # Security: HTTP response headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Custom Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        desc = getattr(e, "description", None)
        return render_template("errors/400.html", error_description=desc), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    with app.app_context():
        # Auto-create tables for fresh databases
        db.create_all()

        # Safely apply migrations if using SQLite database file
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:///"):
            db_path = uri.replace("sqlite:///", "")
            try:
                apply_migrations(db_path)
            except Exception as exc:
                app.logger.warning(f"Migration check skipped: {exc}")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
