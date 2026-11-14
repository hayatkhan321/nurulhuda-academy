"""Family and teacher areas, and the classroom."""
import html
from datetime import timedelta

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from nurulhuda import auth, books, dashboard, db, ledger, mail, pricing, quran_index, video
from nurulhuda.ledger import STATUS_LABELS, aware, now
from nurulhuda.models import ClassReview, ClassSession, CreditEntry, Invoice, Student, Teacher, TeacherCheckin, TeacherEarning
from nurulhuda.routes import _check_form, _f, calculator_input, guess_currency
from nurulhuda.i18n import tr
from nurulhuda.timefmt import ZONE_NAMES, fmt

portal_bp = Blueprint("portal", __name__)


@portal_bp.app_context_processor
def _portal_ctx():
    return {"fmt_time": fmt, "zone_name": lambda z: tr(ZONE_NAMES.get(z, (z or "").replace("_", " "))), "STATUS_LABELS": STATUS_LABELS, "signed_in_role": (
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
    invoices = (Invoice.query.filter(Invoice.family_id == family.id, Invoice.status != "cancelled")
                .order_by(Invoice.created_at.desc()).limit(10).all())
    return render_template("family.html", title="My classes", family=family, upcoming=upcoming, past=past,
                           balance=ledger.balance(family.id), entries=entries, can_flag=ledger.can_flag,
                           joinable=_joinable, invoices=invoices, P=pricing, D=dashboard.family_dashboard(family),
                           presence_of=dashboard.presence_of)


@portal_bp.route("/my/class/<int:cid>/review", methods=["POST"])
@auth.login_required("family")
def review(family, cid):
    """The family rates a class (1 to 5 stars), once."""
    _check_form()
    cs = db.session.get(ClassSession, cid) or abort(404)
    if cs.student.family_id != family.id or cs.status != "completed":
        abort(403)
    try:
        stars = int(request.form.get("stars", 0))
    except ValueError:
        stars = 0
    if 1 <= stars <= 5 and not ClassReview.query.filter_by(class_id=cs.id).first():
        db.session.add(ClassReview(class_id=cs.id, family_id=family.id, teacher_id=cs.teacher_id,
                                   student_id=cs.student_id, stars=stars, comment=_f("comment", 1000)))
        db.session.commit()
        if stars <= 2:
            mail.send_email(current_app.config.get("NOTIFY_EMAIL"), f"Low rating: {stars} star(s) for {cs.teacher.full_name}",
                            f"<p>{html.escape(family.parent_name)} rated {html.escape(cs.student.first_name)}'s class on "
                            f"{fmt(cs.starts_at, 'Asia/Dubai')} with {html.escape(cs.teacher.full_name)}: <b>{stars} of 5</b>.</p>"
                            f"<p>{html.escape(_f('comment', 1000) or 'No comment.')}</p><p>See Admin > Quality.</p>")
    return redirect(url_for("portal.family_home") + "#dashboard")


@portal_bp.route("/my/checkin", methods=["POST"])
@auth.login_required("family")
def checkin(family):
    """After six classes: keep this teacher, or try another of the same standard."""
    _check_form()
    student = db.session.get(Student, request.form.get("student_id", type=int) or 0)
    teacher = db.session.get(Teacher, request.form.get("teacher_id", type=int) or 0)
    choice = request.form.get("choice")
    if not student or student.family_id != family.id or not teacher or choice not in ("keep", "change"):
        abort(400)
    if not TeacherCheckin.query.filter_by(student_id=student.id, teacher_id=teacher.id).first():
        db.session.add(TeacherCheckin(student_id=student.id, teacher_id=teacher.id, choice=choice, note=_f("note", 500),
                                      handled=(choice == "keep")))
        db.session.commit()
        if choice == "change":
            mail.send_email(current_app.config.get("NOTIFY_EMAIL"), f"Teacher change requested: {student.first_name}",
                            f"<p>{html.escape(family.parent_name)} would like {html.escape(student.first_name)} to try another "
                            f"teacher instead of {html.escape(teacher.full_name)}.</p><p>Note: {html.escape(_f('note', 500) or '-')}</p>"
                            "<p>Please arrange a teacher of the same standard and tell the family at least 48 hours before the "
                            "first class with the new teacher. Mark it done in Admin > Quality.</p>")
    return redirect(url_for("portal.family_home") + "#dashboard")


@portal_bp.route("/my/teacher-preference", methods=["POST"])
@auth.login_required("family")
def teacher_pref(family):
    _check_form()
    if request.form.get("pref") in ("same", "open"):
        family.teacher_pref = request.form["pref"]
        db.session.commit()
    return redirect(url_for("portal.family_home") + "#dashboard")


# --- paying for classes --------------------------------------------------------------------------
STATUS_WORDS = {"pending": "Waiting for payment", "reported": "Payment being checked", "paid": "Paid",
                "cancelled": "Cancelled"}


@portal_bp.route("/my/pay", methods=["GET", "POST"])
@auth.login_required("family")
def pay(family):
    cur = guess_currency()
    kids = [k for k in family.students if k.active] or family.students
    choices, months, code = calculator_input(max_children=max(4, len(kids)))
    q = pricing.quote(cur, choices, months, code) if choices else None
    if request.method == "POST":
        _check_form()
        if request.form.get("action") == "create" and q and q.lines and not q.error:
            inv = pricing.make_invoice(family, q)
            db.session.commit()
            link = url_for("portal.invoice", number=inv.number, _external=True)
            mail.send_email(family.email, f"Your invoice {inv.number}: {pricing.money(inv.total, inv.currency)}",
                            f"<p>Assalamu alaikum {html.escape(family.parent_name)},</p><p>Thank you for choosing "
                            f"Nurul Huda Academy. Your invoice <b>{inv.number}</b> is for "
                            f"<b>{pricing.money(inv.total, inv.currency)}</b> ({inv.classes} classes).</p>"
                            f"<p>Please write <b>{inv.number}</b> as the reference when you pay. The ways to pay are "
                            f'on your invoice page: <a href="{link}">{link}</a></p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>')
            return redirect(url_for("portal.invoice", number=inv.number))
    return render_template("pay.html", title="Pay for classes", family=family, kids=kids, P=pricing, cur=cur,
                           plans=pricing.price_list(cur), q=q, months=months, code=code, choices=choices)


@portal_bp.route("/my/invoice/<number>", methods=["GET", "POST"])
@auth.login_required("family")
def invoice(family, number):
    inv = Invoice.query.filter_by(number=number).first() or abort(404)
    if inv.family_id != family.id:
        abort(404)
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "reported" and inv.status in ("pending", "reported"):
            method = request.form.get("method", "")
            inv.method = method if method in pricing.METHODS else "other"
            inv.payer_reference = _f("reference", 200)
            inv.status, inv.reported_at = "reported", now()
            db.session.commit()
            mail.send_email(current_app.config.get("NOTIFY_EMAIL"),
                            f"Payment to check: {inv.number}, {pricing.money(inv.total, inv.currency)}",
                            f"<p>{html.escape(family.parent_name)} says they paid invoice <b>{inv.number}</b> "
                            f"({pricing.money(inv.total, inv.currency)}) by {html.escape(pricing.METHODS.get(inv.method, {}).get('name', 'other'))}.</p>"
                            f"<p>Their reference: {html.escape(inv.payer_reference or '-')}</p>"
                            "<p>Check your account, then confirm it in the admin area (Payments). The classes are added "
                            "to the family when you confirm.</p>")
        elif action == "cancel" and inv.status == "pending":
            inv.status = "cancelled"
            db.session.commit()
            return redirect(url_for("portal.family_home"))
        return redirect(url_for("portal.invoice", number=inv.number))
    return render_template("invoice.html", title=f"Invoice {inv.number}", family=family, inv=inv, P=pricing,
                           lines=pricing.invoice_lines(inv), methods=pricing.methods_on(), STATUS_WORDS=STATUS_WORDS)


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
        books.log("problem_reported", "class", cs.id, reason=reason[:300])
        db.session.commit()
        mail.send_email(current_app.config.get("NOTIFY_EMAIL"), f"Problem reported: class #{cs.id} ({cs.teacher.full_name})",
                        f"<p>{html.escape(family.parent_name)} reported a problem with {html.escape(cs.student.first_name)}'s "
                        f"class on {fmt(cs.starts_at, 'Asia/Dubai')} with {html.escape(cs.teacher.full_name)}.</p>"
                        f"<p><b>What they said:</b> {html.escape(reason)}</p><p>The teacher's pay for this class is on hold "
                        "until you decide in the admin area (Problems).</p>")
    return redirect(url_for("portal.family_home"))


@portal_bp.route("/my/receipt/<int:eid>")
@auth.login_required("family")
def receipt(family, eid):
    e = db.session.get(CreditEntry, eid) or abort(404)
    if e.family_id != family.id or not e.receipt_no:
        abort(404)
    return render_template("receipt.html", e=e, fam=family, business=ledger.get_setting("business_details", ""))


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
    last_prog = {}
    for c in ClassSession.query.filter(ClassSession.teacher_id == teacher.id, ClassSession.prog_book.isnot(None)).order_by(ClassSession.starts_at):
        last_prog[c.student_id] = c
    return render_template("teacher.html", title="My teaching", teacher=teacher, upcoming=upcoming, to_mark=to_mark,
                           past=past, owed=owed, held=held, paid=paid, joinable=_joinable, last_prog=last_prog,
                           SURAHS=quran_index.NAMES, QAIDA=dashboard.QAIDA_LESSONS)


@portal_bp.route("/teacher/class/<int:cid>/mark", methods=["POST"])
@auth.login_required("teacher")
def mark(teacher, cid):
    _check_form()
    cs = db.session.get(ClassSession, cid) or abort(404)
    if cs.teacher_id != teacher.id or cs.status != "scheduled" or aware(cs.starts_at) > now():
        abort(403)
    status = request.form.get("status")
    if status in ("completed", "student_missed") and not books.is_closed(cs.starts_at):
        before = ledger.balance(cs.student.family_id)
        ledger.set_status(cs, status, _f("note", 2000))
        books.log("class_marked", "class", cs.id, status=status)
        if status == "completed":
            book = request.form.get("book")
            num = lambda k: request.form.get(k, type=int)
            if book == "quran" and num("surah") and 1 <= num("surah") <= 114:
                cs.prog_book, cs.prog_surah = "quran", num("surah")
                cs.prog_verse = max(1, min(quran_index.VERSES[cs.prog_surah - 1], num("verse") or 1))
            elif book == "qaida" and num("lesson"):
                cs.prog_book, cs.prog_lesson = "qaida", max(1, min(dashboard.QAIDA_LESSONS, num("lesson")))
            cs.prog_focus = _f("focus", 120)
        db.session.commit()
        after = ledger.balance(cs.student.family_id)
        if after < before:
            mail.low_balance_reminder(cs.student.family, after)
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
    if not cs.room_name:
        # Every class needs one fixed room name so the teacher and the family meet in the same room.
        import secrets
        cs.room_name = "nh-" + secrets.token_hex(8)
        db.session.commit()
    try:
        url = video.room_url(cs)
        tok = video.token(cs, name, owner=(role == "teacher"), observer=(role == "observer"))
    except video.VideoError:
        current_app.logger.exception("Classroom could not open for class %s", cs.id)
        return render_template("room.html", title="Classroom", cs=cs, role=role, state="error"), 503
    return render_template("room.html", title="Classroom", cs=cs, role=role, state="open", url=url, token=tok)


@portal_bp.route("/class/<int:cid>/beat", methods=["POST"])
def beat(cid):
    """Every 30 seconds the classroom says: still in the call, window in view or not, camera on or not.
    Time is added from the previous beat (at most 40 seconds), only around the class's own time."""
    from flask import session
    if request.headers.get("X-CSRF") != session.get("csrf"):
        abort(400)
    cs = db.session.get(ClassSession, cid) or abort(404)
    role, _ = _who_for(cs)
    if role not in ("teacher", "student"):
        return jsonify(ok=True)
    start = aware(cs.starts_at)
    t = now()
    if not (start - timedelta(minutes=15) <= t <= start + timedelta(minutes=(cs.minutes or 30) + 30)):
        return jsonify(ok=True)
    d = request.get_json(silent=True) or {}
    p = "t_" if role == "teacher" else "s_"
    last = getattr(cs, p + "beat_at")
    secs = 0
    if last is not None:
        secs = int(max(0, min(40, (t - aware(last)).total_seconds())))
    setattr(cs, p + "beat_at", t)
    if secs:
        setattr(cs, p + "secs", (getattr(cs, p + "secs") or 0) + secs)
        if d.get("view"):
            setattr(cs, p + "view_secs", (getattr(cs, p + "view_secs") or 0) + secs)
        if d.get("cam"):
            setattr(cs, p + "cam_secs", (getattr(cs, p + "cam_secs") or 0) + secs)
    if role == "teacher":
        cs.t_marks = (cs.t_marks or 0) + max(0, min(500, int(d.get("marks") or 0)))
    db.session.commit()
    return jsonify(ok=True)


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
