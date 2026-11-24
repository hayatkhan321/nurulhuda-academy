from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()

# The project's spare Vercel address. Page views there are sent to the main site so Google sees one address.
SPARE_HOSTS = {"nurulhuda-academy-1pw6.vercel.app"}
# Never redirect these: scheduled jobs and webhooks may still call the vercel.app address.
NO_REDIRECT_PREFIXES = ("/cron", "/whatsapp", "/api")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(days=30)
    db.init_app(app)

    from nurulhuda import models  # noqa: F401
    from nurulhuda.admin import admin_bp
    from nurulhuda.portal import portal_bp
    from nurulhuda.recite import recite_bp
    from nurulhuda.routes import site_bp

    from nurulhuda import i18n
    i18n.init_app(app)

    @app.before_request
    def _spare_host_to_main_site():
        from flask import redirect, request
        host = (request.host or "").split(":")[0].lower()
        if host not in SPARE_HOSTS or request.method not in ("GET", "HEAD"):
            return None
        if request.path.startswith(NO_REDIRECT_PREFIXES):
            return None
        base = (app.config.get("SITE_URL") or "").rstrip("/")
        if not base or host in base:
            return None
        target = base + request.full_path if request.query_string else base + request.path
        return redirect(target, code=308)

    app.register_blueprint(site_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(recite_bp)

    @app.errorhandler(413)
    def _too_large(_e):
        from flask import render_template
        return render_template("teach.html", page="teach", title="Teach with us", form={},
                               errors={"_save": "Your files were too large to send. Each upload box takes up to 2 MB. "
                                                "Please choose smaller files and fill in the form again."}), 413

    # Phase 1 has two simple tables, so create them on start-up (Vercel has no release step).
    # Never raise here: a database hiccup must not take the public site down.
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception("Could not create database tables")

    return app
