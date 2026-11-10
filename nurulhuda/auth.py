"""Sign-in by e-mail link for families and teachers (no passwords to forget)."""
import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from flask import abort, redirect, session, url_for

from nurulhuda import db
from nurulhuda.ledger import aware, now
from nurulhuda.models import Family, LoginToken, Teacher

LINK_LIFETIME = timedelta(minutes=30)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def find_account(email: str):
    """Return ('family'|'teacher', row) for an e-mail, preferring an active teacher."""
    email = (email or "").strip().lower()
    t = Teacher.query.filter(db.func.lower(Teacher.email) == email, Teacher.active.is_(True)).first()
    if t:
        return "teacher", t
    f = Family.query.filter(db.func.lower(Family.email) == email).first()
    if f:
        return "family", f
    return None, None


def issue_token(role: str, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.session.add(LoginToken(token_hash=_hash(token), role=role, user_id=user_id, expires_at=now() + LINK_LIFETIME))
    db.session.commit()
    return token


def redeem(token: str):
    row = LoginToken.query.filter_by(token_hash=_hash(token)).first()
    if not row or row.used_at or aware(row.expires_at) < now():
        return None
    row.used_at = now()
    db.session.commit()
    session.clear()
    session["role"], session["uid"] = row.role, row.user_id
    session.permanent = True
    return row.role


def current_family():
    if session.get("role") == "family":
        return db.session.get(Family, session.get("uid"))
    return None


def current_teacher():
    if session.get("role") == "teacher":
        t = db.session.get(Teacher, session.get("uid"))
        return t if t and t.active else None
    return None


def is_admin() -> bool:
    return bool(session.get("admin"))


def login_required(role):
    def deco(fn):
        @wraps(fn)
        def inner(*a, **kw):
            who = current_family() if role == "family" else current_teacher()
            if not who:
                return redirect(url_for("portal.login"))
            return fn(who, *a, **kw)
        return inner
    return deco


def admin_required(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if not is_admin():
            return redirect(url_for("site.admin"))
        return fn(*a, **kw)
    return inner


def forbid():
    abort(403)
