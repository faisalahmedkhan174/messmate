import os
from flask import Flask, redirect, url_for, session

from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

    db.init_app(app)

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
    
    @app.context_processor
    def inject_globals():
        return {
            "session_mess_name": session.get("mess_name"),
            "session_manager_name": session.get("manager_name"),
        }

    @app.errorhandler(404)
    def not_found(e):
        return "Page not found.", 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return "Something went wrong on our end. Please try again.", 500

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
