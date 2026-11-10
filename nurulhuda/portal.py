"""Family and teacher areas, and the classroom."""
import html
from datetime import timedelta

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from nurulhuda import auth, db, ledger, mail, video
from nurulhuda.ledger import STATUS_LABELS, aware, now
from nurulhuda.models import ClassSession, CreditEntry, Student, TeacherEarning
from nurulhuda.routes import _check_form, _f
from nurulhuda.timefmt import ZONE_NAMES, fmt

portal_bp = Blueprint("portal", __name__)


@portal_bp.app_context_processor
def _portal_ctx():
    return {"fmt_time": fmt, "zone_name": lambda z: ZONE_NAMES.get(z, (z or "").replace("_", " ")), "STATUS_LABELS": STATUS_LABELS, "signed_in_role": (
        "family" if auth.current_family() else "teacher" if auth.current_teacher() else None)}


@portal_bp.after_app_request
def _private(resp):
    if request.path.startswith(("/my", "/teacher", "/class", "/login")):
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
    return resp


# --- sign in ------------------------------------------------------------------------------------
@portal_bp.route("/login", methods=["GET", "POST"])
def login():
    if auth.current_teacher():
        return redirect(url_for("portal.teacher_home"))
    if auth.current_family():
        return redirect(url_for("portal.family_home"))
    if request.method == "POST":
        _check_form()
        role, who = auth.find_account(_f("email"))
        if who:
            link = url_for("portal.login_link", token=auth.issue_token(role, who.id), _external=True)
            name = who.parent_name if role == "family" else who.full_name
            mail.send_email(who.email, "Your sign-in link for Nurul Huda Academy",
                            f"<p>Assalamu alaikum {html.escape(name)},</p><p>Tap the button to sign in. "
                            "The link works once and expires in 30 minutes.</p>"
                            f'<p style="margin:24px 0"><a href="{link}" style="background:#0b5d45;color:#fff;'
                            'padding:12px 22px;border-radius:999px;text-decoration:none;font-weight:bold">Sign in</a></p>'
                            "<p>If you did not ask for this, you can ignore this e-mail.</p>")
        # Same message either way, so the page never reveals who is registered.
        return render_template("login.html", title="Sign in", sent=True)
    return render_template("login.html", title="Sign in", sent=False)


@portal_bp.route("/login/<token>")
def login_link(token):
    role = auth.redeem(token)
    if not role:
        return render_template("login.html", title="Sign in", sent=False,
                               error="That sign-in link has expired or was already used. Ask for a new one below."), 400
    return redirect(url_for("portal.teacher_home" if role == "teacher" else "portal.family_home"))


@portal_bp.route("/logout")
def logout():
    keep_admin = auth.is_admin()
    from flask import session
    session.pop("role", None)
    session.pop("uid", None)
    if keep_admin:
        session["admin"] = True
    return redirect(url_for("site.home"))


# --- family -------------------------------------------------------------------------------------
@portal_bp.route("/my")
@auth.login_required("family")
def family_home(family):
    student_ids = [s.id for s in family.students]
    q = ClassSession.query.filter(ClassSession.student_id.in_(student_ids or [0]))
    soon = now() - timedelta(hours=2)
    upcoming = q.filter(ClassSession.status == "scheduled", ClassSession.starts_at >= soon).order_by(ClassSession.starts_at).limit(20).all()
    past = q.filter(ClassSession.status != "scheduled").order_by(ClassSession.starts_at.desc()).limit(30).all()
    entries = CreditEntry.query.filter_by(family_id=family.id).order_by(CreditEntry.created_at.desc()).limit(20).all()
    return render_template("family.html", title="My classes", family=family, upcoming=upcoming, past=past,
                           balance=ledger.balance(family.id), entries=entries, can_flag=ledger.can_flag,
                           joinable=_joinable)


@portal_bp.route("/my/class/<int:cid>/report", methods=["POST"])
@auth.login_required("family")
def report(family, cid):
    _check_form()
    cs = db.session.get(ClassSession, cid) or abort(404)
    if cs.student.family_id != family.id:
        abort(403)
    reason = _f("reason", 2000)
    if reason and ledger.can_flag(cs):
        ledger.flag(cs, reason)
        db.session.commit()
        mail.send_email(current_app.config.get("NOTIFY_EMAIL"), f"Problem reported: class #{cs.id} ({cs.teacher.full_name})",
                        f"<p>{html.escape(family.parent_name)} reported a problem with {html.escape(cs.student.first_name)}'s "
                        f"class on {fmt(cs.starts_at, 'Asia/Dubai')} with {html.escape(cs.teacher.full_name)}.</p>"
                        f"<p><b>What they said:</b> {html.escape(reason)}</p><p>The teacher's pay for this class is on hold "
                        "until you decide in the admin area (Problems).</p>")
    return redirect(url_for("portal.family_home"))


# --- teacher ------------------------------------------------------------------------------------
@portal_bp.route("/teacher")
@auth.login_required("teacher")
def teacher_home(teacher):
    q = ClassSession.query.filter_by(teacher_id=teacher.id)
    soon = now() - timedelta(hours=2)
    upcoming = q.filter(ClassSession.status == "scheduled", ClassSession.starts_at >= soon).order_by(ClassSession.starts_at).limit(30).all()
    to_mark = q.filter(ClassSession.status == "scheduled", ClassSession.starts_at < now()).order_by(ClassSession.starts_at).all()
    past = q.filter(ClassSession.status != "scheduled").order_by(ClassSession.starts_at.desc()).limit(30).all()
    earn = TeacherEarning.query.filter_by(teacher_id=teacher.id)
    owed = sum((e.amount for e in earn.filter_by(status="owed")), 0)
    held = sum((e.amount for e in earn.filter_by(status="held")), 0)
    paid = sum((e.amount for e in earn.filter_by(status="paid")), 0)
    return render_template("teacher.html", title="My teaching", teacher=teacher, upcoming=upcoming, to_mark=to_mark,
                           past=past, owed=owed, held=held, paid=paid, joinable=_joinable)


@portal_bp.route("/teacher/class/<int:cid>/mark", methods=["POST"])
@auth.login_required("teacher")
def mark(teacher, cid):
    _check_form()
    cs = db.session.get(ClassSession, cid) or abort(404)
    if cs.teacher_id != teacher.id or cs.status != "scheduled" or aware(cs.starts_at) > now():
        abort(403)
    status = request.form.get("status")
    if status in ("completed", "student_missed"):
        ledger.set_status(cs, status, _f("note", 2000))
        db.session.commit()
    return redirect(url_for("portal.teacher_home"))


# --- classroom ----------------------------------------------------------------------------------
def _joinable(cs) -> bool:
    start = aware(cs.starts_at)
    return cs.status == "scheduled" and start - timedelta(minutes=15) <= now() <= start + timedelta(minutes=cs.minutes + 30)


def _who_for(cs):
    """Return (role, display name) for the person opening this class, or abort."""
    t, f = auth.current_teacher(), auth.current_family()
    if t and t.id == cs.teacher_id:
        return "teacher", t.full_name
    if f and cs.student.family_id == f.id:
        return "student", cs.student.first_name
    if auth.is_admin():
        return "observer", "Supervisor"
    abort(403)


@portal_bp.route("/class/<int:cid>")
def room(cid):
    cs = db.session.get(ClassSession, cid) or abort(404)
    if not (auth.current_teacher() or auth.current_family() or auth.is_admin()):
        return redirect(url_for("portal.login"))
    role, name = _who_for(cs)
    if role != "observer" and not _joinable(cs):
        return render_template("room.html", title="Classroom", cs=cs, role=role, state="closed")
    if not video.configured():
        return render_template("room.html", title="Classroom", cs=cs, role=role, state="not_configured")
    try:
        url = video.room_url(cs)
        tok = video.token(cs, name, owner=(role == "teacher"), observer=(role == "observer"))
    except video.VideoError:
        current_app.logger.exception("Classroom could not open for class %s", cs.id)
        return render_template("room.html", title="Classroom", cs=cs, role=role, state="error"), 503
    return render_template("room.html", title="Classroom", cs=cs, role=role, state="open", url=url, token=tok)


@portal_bp.route("/class/<int:cid>/joined", methods=["POST"])
def joined(cid):
    from flask import session
    if request.headers.get("X-CSRF") != session.get("csrf"):
        abort(400)
    cs = db.session.get(ClassSession, cid) or abort(404)
    role, _ = _who_for(cs)
    if role == "teacher" and not cs.teacher_joined_at:
        cs.teacher_joined_at = now()
    elif role == "student" and not cs.student_joined_at:
        cs.student_joined_at = now()
    db.session.commit()
    return jsonify(ok=True)
