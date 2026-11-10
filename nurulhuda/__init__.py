from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from nurulhuda import models  # noqa: F401
    from nurulhuda.routes import site_bp

    app.register_blueprint(site_bp)

    # Phase 1 has two simple tables, so create them on start-up (Vercel has no release step).
    # Never raise here: a database hiccup must not take the public site down.
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception("Could not create database tables")

    return app
