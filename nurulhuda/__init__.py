from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(days=30)
    db.init_app(app)

    from nurulhuda import models  # noqa: F401
    from nurulhuda.admin import admin_bp
    from nurulhuda.portal import portal_bp
    from nurulhuda.routes import site_bp

    app.register_blueprint(site_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(admin_bp)

    # Phase 1 has two simple tables, so create them on start-up (Vercel has no release step).
    # Never raise here: a database hiccup must not take the public site down.
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception("Could not create database tables")

    return app
