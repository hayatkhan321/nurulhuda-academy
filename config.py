import os

from dotenv import load_dotenv

load_dotenv()

IS_VERCEL = bool(os.getenv("VERCEL"))


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        # Local fallback only. On Vercel /tmp is wiped regularly, so set DATABASE_URL (Supabase Postgres) there.
        return "sqlite:////tmp/nurulhuda.db" if IS_VERCEL else "sqlite:///nurulhuda_local.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    IS_PRODUCTION = APP_ENV.lower() == "production"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-now")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    SITE_URL = os.getenv("SITE_URL", "https://www.nurulhudaacademy.org")
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "nurulhudaacademy2@gmail.com")

    # E-mail goes through Resend (https://resend.com) when RESEND_API_KEY is set, as on hayatclinics.com.
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "Nurul Huda Academy <hello@nurulhudaacademy.org>")
    MAIL_REPLY_TO = os.getenv("MAIL_REPLY_TO", CONTACT_EMAIL)
    # Where new trial requests and teacher applications are announced.
    NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", CONTACT_EMAIL)

    # Password for /admin, the list of sign-ups. Leave empty to keep /admin switched off.
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
