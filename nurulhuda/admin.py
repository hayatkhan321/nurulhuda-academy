"""Founders' tools: families, teachers, packages, scheduling, payments received, problems and teacher payouts."""
import csv
import html
import io
import secrets
from datetime import timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for

from nurulhuda import auth, db, ledger, mail
from nurulhuda.ledger import now
from nurulhuda.models import (ClassSession, CreditEntry, Family, Package, Payout, Student, Teacher,
                              TeacherApplication, TeacherEarning, TrialRequest)
from nurulhuda.routes import _check_form, _f
from nurulhuda.timefmt import ZONES, fmt, parse_local, tz

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
CURRENCIES = ["USD", "CAD", "GBP", "AED", "PKR", "EGP"]


@admin_bp.app_context_processor
def _admin_ctx():
    return {"ZONES": ZONES, "CURRENCIES": CURRENCIES}


def _money(name):
    try:
        return Decimal(_f(name, 20) or "0").quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _int(name, default=0):
    try:
        return int(_f(name, 10) or default)
    except ValueError:
        return default


def _notify_scheduled(classes):
    if not classes:
        return
    cs = classes[0]
    fam, t = cs.student.family, cs.teacher
    rows_f = "".join(f"<li>{fmt(c.starts_at, fam.timezone)}</li>" for c in classes)
    rows_t = "".join(f"<li>{fmt(c.starts_at, t.timezone)}</li>" for c in classes)
    login = url_for("portal.login", _external=True)
    mail.send_email(fam.email, f"Classes scheduled for {cs.student.first_name}",
                    f"<p>Assalamu alaikum {html.escape(fam.parent_name)},</p><p>{html.escape(cs.student.first_name)}'s "
                    f"classes with {html.escape(t.full_name)} ({cs.minutes} minutes):</p><ul>{rows_f}</ul>"
                    f'<p>To join, sign in at <a href="{login}">{login}</a> a few minutes before the class and tap '
                    "<b>Join class</b>.</p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>")
    mail.send_email(t.email, f"New classes: {cs.student.first_name}",
                    f"<p>Assalamu alaikum {html.escape(t.full_name)},</p><p>New classes with "
                    f"{html.escape(cs.student.first_name)} (age {html.escape(cs.student.age or '-')}, "
                    f"{html.escape(cs.student.course or '')}):</p><ul>{rows_t}</ul>"
                    f'<p>Sign in at <a href="{login}">{login}</a> to join, and mark each class afterwards.</p>')


# --- families -------------------------------------------------------------------------------------
@admin_bp.route("/families")
@auth.admin_required
def families():
    rows = Family.query.order_by(Family.created_at.desc()).all()
    return render_template("admin/families.html", title="Families", tab="families", rows=rows, balance=ledger.balance)


@admin_bp.route("/families/new", methods=["GET", "POST"])
@auth.admin_required
def family_new():
    trial = db.session.get(TrialRequest, request.args.get("trial", type=int) or 0)
    if request.method == "POST":
        _check_form()
        email = _f("email").lower()
        if not _f("parent_name") or "@" not in email:
            return render_template("admin/family_form.html", title="New family", tab="families", trial=trial,
                                   error="Enter the parent's name and a valid e-mail."), 400
        if Family.query.filter(db.func.lower(Family.email) == email).first():
            return render_template("admin/family_form.html", title="New family", tab="families", trial=trial,
                                   error="A family with that e-mail already exists."), 400
        fam = Family(parent_name=_f("parent_name", 120), email=email, phone=_f("phone", 40), country=_f("country", 60),
                     timezone=_f("timezone", 60) or "America/Toronto", teacher_gender=_f("teacher_gender", 20),
                     recording_consent=bool(request.form.get("recording_consent")))
        db.session.add(fam)
        db.session.flush()
        if _f("student_name"):
            db.session.add(Student(family_id=fam.id, first_name=_f("student_name", 80), age=_f("student_age", 20),
                                   course=_f("course", 60)))
        if trial:
            trial.status = "converted"
        db.session.commit()
        return redirect(url_for("admin.family", fid=fam.id))
    return render_template("admin/family_form.html", title="New family", tab="families", trial=trial)


@admin_bp.route("/families/<int:fid>", methods=["GET", "POST"])
@auth.admin_required
def family(fid):
    fam = db.session.get(Family, fid) or abort(404)
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "student" and _f("first_name"):
            db.session.add(Student(family_id=fam.id, first_name=_f("first_name", 80), age=_f("age", 20),
                                   course=_f("course", 60), level=_f("level", 120)))
        elif action == "payment":
            pkg = db.session.get(Package, _int("package_id"))
            amount = _money("amount")
            if pkg and amount is not None:
                db.session.add(CreditEntry(family_id=fam.id, classes=pkg.classes, kind="purchase", amount=amount,
                                           currency=_f("currency", 3) or pkg.currency, method=_f("method", 40),
                                           reference=_f("reference", 200), package_id=pkg.id, note=pkg.name))
        elif action == "adjust" and _int("classes"):
            db.session.add(CreditEntry(family_id=fam.id, classes=_int("classes"), kind="adjustment",
                                       note=_f("note", 300) or "Manual adjustment"))
        elif action == "refund":
            amount = _money("amount")
            if amount:
                db.session.add(CreditEntry(family_id=fam.id, classes=-abs(_int("classes")), kind="refund",
                                           amount=-amount, currency=_f("currency", 3), method=_f("method", 40),
                                           reference=_f("reference", 200), note="Refund"))
        elif action == "details":
            fam.phone, fam.country = _f("phone", 40), _f("country", 60)
            fam.timezone = _f("timezone", 60) or fam.timezone
            fam.recording_consent = bool(request.form.get("recording_consent"))
            fam.notes = _f("notes", 3000)
        db.session.commit()
        return redirect(url_for("admin.family", fid=fam.id))
    sids = [s.id for s in fam.students] or [0]
    classes = ClassSession.query.filter(ClassSession.student_id.in_(sids)).order_by(ClassSession.starts_at.desc()).limit(50).all()
    entries = CreditEntry.query.filter_by(family_id=fam.id).order_by(CreditEntry.created_at.desc()).all()
    return render_template("admin/family.html", title=fam.parent_name, tab="families", fam=fam, classes=classes,
                           entries=entries, balance=ledger.balance(fam.id),
                           packages=Package.query.filter_by(active=True).order_by(Package.classes).all())


# --- teachers -------------------------------------------------------------------------------------
@admin_bp.route("/teachers", methods=["GET", "POST"])
@auth.admin_required
def teachers():
    error = None
    if request.method == "POST":
        _check_form()
        if request.form.get("action") == "limit":
            ledger.set_setting("teacher_limit", str(max(1, _int("limit", 5))))
            db.session.commit()
        elif request.form.get("action") == "toggle":
            t = db.session.get(Teacher, _int("teacher_id")) or abort(404)
            if not t.active and ledger.active_teacher_count() >= ledger.teacher_limit():
                error = (f"You already have {ledger.teacher_limit()} active teachers, the current limit. "
                         "Raise the limit or pause another teacher first.")
            elif not t.active and not t.rate:
                error = f"Set {t.full_name}'s pay per class before activating."
            else:
                t.active = not t.active
                db.session.commit()
        if not error:
            return redirect(url_for("admin.teachers"))
    rows = Teacher.query.order_by(Teacher.active.desc(), Teacher.full_name).all()
    return render_template("admin/teachers.html", title="Teachers", tab="teachers", rows=rows, error=error,
                           limit=ledger.teacher_limit(), active=ledger.active_teacher_count())


@admin_bp.route("/teachers/new", methods=["GET", "POST"])
@admin_bp.route("/teachers/<int:tid>", methods=["GET", "POST"])
@auth.admin_required
def teacher(tid=None):
    t = db.session.get(Teacher, tid) if tid else None
    app = db.session.get(TeacherApplication, request.args.get("app", type=int) or 0)
    if request.method == "POST":
        _check_form()
        email = _f("email").lower()
        rate = _money("rate")
        clash = Teacher.query.filter(db.func.lower(Teacher.email) == email, Teacher.id != (t.id if t else 0)).first()
        if not _f("full_name") or "@" not in email or rate is None or clash:
            return render_template("admin/teacher_form.html", title="Teacher", tab="teachers", t=t, app=app,
                                   error="Enter a name, a unique e-mail and a valid pay per class."), 400
        if not t:
            t = Teacher(active=False, application_id=app.id if app else None)
            db.session.add(t)
            if app:
                app.status = "approved"
        t.full_name, t.email, t.phone = _f("full_name", 120), email, _f("phone", 40)
        t.country, t.timezone, t.gender = _f("country", 60), _f("timezone", 60) or "Asia/Karachi", _f("gender", 20)
        t.levels, t.rate, t.rate_currency = _f("levels", 200), rate, _f("rate_currency", 3) or "USD"
        t.payout_method = _f("payout_method", 200)
        db.session.commit()
        return redirect(url_for("admin.teachers"))
    return render_template("admin/teacher_form.html", title="Teacher", tab="teachers", t=t, app=app)


# --- packages -------------------------------------------------------------------------------------
@admin_bp.route("/packages", methods=["GET", "POST"])
@auth.admin_required
def packages():
    if request.method == "POST":
        _check_form()
        pid = _int("package_id")
        p = db.session.get(Package, pid) if pid else None
        if request.form.get("action") == "toggle" and p:
            p.active = not p.active
        else:
            price = _money("price")
            if _f("name") and _int("classes") > 0 and price is not None:
                p = p or Package()
                p.name, p.classes, p.minutes = _f("name", 80), _int("classes"), _int("minutes", 30)
                p.price, p.currency = price, _f("currency", 3) or "USD"
                db.session.add(p)
        db.session.commit()
        return redirect(url_for("admin.packages"))
    rows = Package.query.order_by(Package.active.desc(), Package.currency, Package.classes).all()
    return render_template("admin/packages.html", title="Packages", tab="packages", rows=rows)


# --- classes --------------------------------------------------------------------------------------
@admin_bp.route("/classes", methods=["GET", "POST"])
@auth.admin_required
def classes():
    error = None
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "schedule":
            st = db.session.get(Student, _int("student_id"))
            t = db.session.get(Teacher, _int("teacher_id"))
            try:
                first = parse_local(_f("date"), _f("time"), _f("timezone"))
            except ValueError:
                first = None
            weeks = max(1, min(_int("weeks", 1), 26))
            if not (st and t and t.active and first):
                error = "Choose a student, an active teacher, a date and a time."
            else:
                zone = tz(_f("timezone"))
                local0 = first.astimezone(zone)                       # first class, in the chosen time zone
                days = sorted({int(d) for d in request.form.getlist("days") if d.isdigit()} or {local0.weekday()})
                monday = local0 - timedelta(days=local0.weekday())     # same clock time, Monday of that week
                made = []
                for w in range(weeks):
                    for d in days:
                        when_local = monday + timedelta(weeks=w, days=d)
                        if when_local < local0:
                            continue
                        cs = ClassSession(student_id=st.id, teacher_id=t.id,
                                          starts_at=when_local.astimezone(timezone.utc), minutes=_int("minutes", 30),
                                          room_name="nh-" + secrets.token_hex(8))
                        db.session.add(cs)
                        made.append(cs)
                db.session.commit()
                made.sort(key=lambda c: c.starts_at)
                if request.form.get("notify"):
                    _notify_scheduled(made)
                return redirect(url_for("admin.classes"))
        elif action in ("status", "cancel"):
            cs = db.session.get(ClassSession, _int("class_id")) or abort(404)
            ledger.set_status(cs, "cancelled" if action == "cancel" else _f("status", 20))
            db.session.commit()
            return redirect(url_for("admin.classes"))
    start = now() - timedelta(days=2)
    rows = ClassSession.query.filter(ClassSession.starts_at >= start).order_by(ClassSession.starts_at).limit(300).all()
    unmarked = ClassSession.query.filter(ClassSession.status == "scheduled",
                                         ClassSession.starts_at < now() - timedelta(hours=1)).count()
    students = Student.query.filter_by(active=True).join(Family).order_by(Family.parent_name, Student.first_name).all()
    return render_template("admin/classes.html", title="Classes", tab="classes", rows=rows, error=error,
                           students=students, teachers=Teacher.query.filter_by(active=True).order_by(Teacher.full_name).all(),
                           unmarked=unmarked, joinable=lambda c: c.status == "scheduled")


# --- problems -------------------------------------------------------------------------------------
@admin_bp.route("/problems", methods=["GET", "POST"])
@auth.admin_required
def problems():
    if request.method == "POST":
        _check_form()
        cs = db.session.get(ClassSession, _int("class_id")) or abort(404)
        decision = request.form.get("decision")
        if decision in ("pay", "refund"):
            ledger.resolve(cs, decision, _f("note", 180))
            db.session.commit()
        return redirect(url_for("admin.problems"))
    open_rows = ClassSession.query.filter(ClassSession.flagged_at.isnot(None), ClassSession.flag_resolution.is_(None)).all()
    done = (ClassSession.query.filter(ClassSession.flag_resolution.isnot(None))
            .order_by(ClassSession.flagged_at.desc()).limit(30).all())
    return render_template("admin/problems.html", title="Problems", tab="problems", open_rows=open_rows, done=done)


# --- payouts --------------------------------------------------------------------------------------
def _owed():
    out = []
    for t in Teacher.query.order_by(Teacher.full_name).all():
        rows = TeacherEarning.query.filter_by(teacher_id=t.id, status="owed").all()
        held = TeacherEarning.query.filter_by(teacher_id=t.id, status="held").count()
        if rows or held:
            out.append({"t": t, "rows": rows, "total": sum((r.amount for r in rows), Decimal("0")),
                        "currency": t.rate_currency, "held": held})
    return out


@admin_bp.route("/payouts", methods=["GET", "POST"])
@auth.admin_required
def payouts():
    if request.method == "POST":
        _check_form()
        t = db.session.get(Teacher, _int("teacher_id")) or abort(404)
        rows = TeacherEarning.query.filter_by(teacher_id=t.id, status="owed").all()
        if rows:
            p = Payout(teacher_id=t.id, amount=sum((r.amount for r in rows), Decimal("0")), currency=t.rate_currency,
                       method=_f("method", 40), reference=_f("reference", 200))
            db.session.add(p)
            db.session.flush()
            for r in rows:
                r.status, r.payout_id = "paid", p.id
            db.session.commit()
        return redirect(url_for("admin.payouts"))
    history = Payout.query.order_by(Payout.created_at.desc()).limit(50).all()
    names = {t.id: t.full_name for t in Teacher.query.all()}
    return render_template("admin/payouts.html", title="Teacher payouts", tab="payouts", owed=_owed(), history=history,
                           names=names)


@admin_bp.route("/payouts.csv")
@auth.admin_required
def payouts_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Teacher", "E-mail", "Country", "Classes", "Amount", "Currency", "Payout details"])
    for o in _owed():
        if o["rows"]:
            w.writerow([o["t"].full_name, o["t"].email, o["t"].country or "", len(o["rows"]), f"{o['total']:.2f}",
                        o["currency"], o["t"].payout_method or ""])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=teacher-payouts-{now():%Y-%m-%d}.csv"})
