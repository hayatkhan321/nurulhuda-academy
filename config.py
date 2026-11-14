import os

from dotenv import load_dotenv

load_dotenv()

IS_VERCEL = bool(os.getenv("VERCEL"))


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    url = _with_password(url, os.getenv("DB_PASSWORD", ""))
    if not url:
        # Local fallback only. On Vercel /tmp is wiped regularly, so set DATABASE_URL (Supabase Postgres) there.
        return "sqlite:////tmp/nurulhuda.db" if IS_VERCEL else "sqlite:///nurulhuda_local.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _with_password(url: str, password: str) -> str:
    """If DB_PASSWORD is set, put it into DATABASE_URL safely, so a password with symbols
    (@ / : # ?) cannot break the address. DATABASE_URL may then be written without a password."""
    if not url or not password:
        return url
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(url)
    host = parts.netloc.rsplit("@", 1)[-1]
    user = parts.netloc.rsplit("@", 1)[0].split(":", 1)[0] if "@" in parts.netloc else ""
    netloc = f"{user}:{quote(password.strip(), safe='')}@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    IS_PRODUCTION = APP_ENV.lower() == "production"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-now")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    # Two upload boxes of 2 MB each, plus the form itself. Vercel refuses anything over 4.5 MB.
    MAX_CONTENT_LENGTH = int(4.4 * 1024 * 1024)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    SITE_URL = os.getenv("SITE_URL", "https://www.nurulhudaacademy.org")
    # Public addresses on the website (ImprovMX forwards both to the academy Gmail).
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "info@nurulhudaacademy.org")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@nurulhudaacademy.org")

    # E-mail goes through Resend (https://resend.com) when RESEND_API_KEY is set, as on hayatclinics.com.
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
    MAIL_FROM = os.getenv("MAIL_FROM", "Nurul Huda Academy <hello@nurulhudaacademy.org>")
    MAIL_REPLY_TO = os.getenv("MAIL_REPLY_TO", CONTACT_EMAIL)
    # Where new trial requests and teacher applications are announced.
    NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "nurulhudaacademy2@gmail.com")

    # Classroom video (https://daily.co). Without it, the classroom page explains that video is not set up yet.
    DAILY_API_KEY = os.getenv("DAILY_API_KEY", "").strip()

    # Claude as bookkeeping reviewer (https://console.anthropic.com). Without a key, the Books page works without it.
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5").strip()
    # Vercel sends this with its scheduled monthly review (set CRON_SECRET in the website settings).
    CRON_SECRET = os.getenv("CRON_SECRET", "").strip()

    # Password for /admin, the list of sign-ups. Leave empty to keep /admin switched off.
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
