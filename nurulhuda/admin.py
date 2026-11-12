"""Founders' tools: families, teachers, packages, scheduling, payments received, problems and teacher payouts."""
import csv
import html
import io
import secrets
from datetime import timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for

from nurulhuda import content as C
from nurulhuda import auth, db, ledger, mail, pricing
from nurulhuda.ledger import now
from nurulhuda.models import (ClassSession, CreditEntry, Family, Invoice, Package, Payout, PromoCode, Student, Teacher,
                              TeacherApplication, TeacherEarning, TrialRequest)
from nurulhuda.routes import _check_form, _f
from nurulhuda.timefmt import ZONES, fmt, parse_local, tz

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
CURRENCIES = ["USD", "GBP", "EUR", "CAD", "AED", "PKR", "EGP"]


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
            fam.instruction_language, fam.site_lang = trial.instruction_language, trial.site_lang or "en"
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
    q = Teacher.query
    # Sort teachers by language strength, e.g. ?english=Fluent shows Native and Fluent English speakers
    order = C.LEVELS_WITH_NONE
    for key, col in (("english", Teacher.english_level), ("urdu", Teacher.urdu_level)):
        want = request.args.get(key, "")
        if want in order:
            q = q.filter(col.in_(order[: order.index(want) + 1]))
    rows = q.order_by(Teacher.active.desc(), Teacher.full_name).all()
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
        t.language_profile = _f("language_profile", 500) or None
        for key in ("english_level", "urdu_level", "arabic_level"):
            setattr(t, key, _f(key, 20) if _f(key) in C.LEVELS_WITH_NONE else None)
        if app and not t.site_lang:
            t.site_lang = app.site_lang or "en"
        db.session.commit()
        return redirect(url_for("admin.teachers"))
    return render_template("admin/teacher_form.html", title="Teacher", tab="teachers", t=t, app=app)


# --- packages, pricing rules and discount codes ------------------------------------------------------
RULE_KEYS = ("price_currencies", "sibling_2", "sibling_3", "upfront_3", "upfront_6", "upfront_12", "max_discount",
             "floor_prices")


@admin_bp.route("/packages", methods=["GET", "POST"])
@auth.admin_required
def packages():
    error = None
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        pid = _int("package_id")
        p = db.session.get(Package, pid) if pid else None
        if action == "toggle" and p:
            p.active = not p.active
        elif action == "price" and p:
            price = _money("price")
            if price is not None and price > 0:
                p.price = price
            p.public = bool(request.form.get("public"))
        elif action == "standard":
            pricing.load_standard_prices()
        elif action == "rules":
            for key in RULE_KEYS:
                val = _f(key, 300)
                if key not in ("price_currencies", "floor_prices"):
                    try:
                        val = str(max(Decimal("0"), min(Decimal("100"), Decimal(val))))
                    except InvalidOperation:
                        error = "Discounts must be numbers between 0 and 100."
                        continue
                if val:
                    ledger.set_setting(key, val)
        elif action == "code":
            code = _f("code", 30).upper().replace(" ", "")
            percent = _money("percent")
            if not code or percent is None or not (0 < percent <= 100):
                error = "A code needs letters or numbers and a discount between 1 and 100%."
            elif PromoCode.query.filter(db.func.upper(PromoCode.code) == code).first():
                error = "That code already exists."
            else:
                from datetime import date
                try:
                    expires = date.fromisoformat(_f("expires_on", 10)) if _f("expires_on") else None
                except ValueError:
                    expires = None
                db.session.add(PromoCode(code=code, percent=percent, kind=_f("kind", 20) or "offer",
                                         beyond_cap=bool(request.form.get("beyond_cap")), expires_on=expires,
                                         max_uses=_int("max_uses") or None, note=_f("note", 200)))
        elif action == "code_toggle":
            c = db.session.get(PromoCode, _int("code_id")) or abort(404)
            c.active = not c.active
        else:
            price = _money("price")
            if _f("name") and _int("classes") > 0 and price is not None:
                p = p or Package()
                p.name, p.classes, p.minutes = _f("name", 80), _int("classes"), _int("minutes", 30)
                p.price, p.currency = price, _f("currency", 3) or "USD"
                p.plan = (_f("plan", 40) or p.name).lower().replace(" ", "-")[:40]
                p.blurb, p.sort, p.public = _f("blurb", 200), _int("sort", 100), bool(request.form.get("public"))
                db.session.add(p)
        if not error:
            db.session.commit()
            return redirect(url_for("admin.packages"))
        db.session.rollback()
    rows = Package.query.order_by(Package.currency, Package.sort, Package.classes).all()
    codes = PromoCode.query.order_by(PromoCode.active.desc(), PromoCode.created_at.desc()).all()
    used = {c.code: Invoice.query.filter(Invoice.promo_code == c.code, Invoice.status == "paid").count() for c in codes}
    return render_template("admin/packages.html", title="Packages and prices", tab="packages", rows=rows, codes=codes,
                           used=used, rules={k: pricing.setting(k) for k in RULE_KEYS}, error=error, P=pricing,
                           floors=pricing.floors())


# --- payments -------------------------------------------------------------------------------------
@admin_bp.route("/payments", methods=["GET", "POST"])
@auth.admin_required
def payments():
    error = None
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "methods":
            order = []
            for key in pricing.METHODS:
                ledger.set_setting(f"pay_{key}_on", "1" if request.form.get(f"{key}_on") else "0")
                ledger.set_setting(f"pay_{key}_link", _f(f"{key}_link", 300))
                ledger.set_setting(f"pay_{key}_details", (request.form.get(f"{key}_details") or "").strip()[:500])
                order.append((_int(f"{key}_order", 9), key))
            ledger.set_setting("pay_order", ",".join(k for _, k in sorted(order)))
        elif action in ("confirm", "cancel", "reopen"):
            inv = db.session.get(Invoice, _int("invoice_id")) or abort(404)
            if action == "confirm" and inv.status in ("pending", "reported"):
                received = _money("amount_received")
                if received is None or received <= 0:
                    error = f"Enter the amount you received for {inv.number}."
                else:
                    method = _f("method", 20) or inv.method or "bank"
                    inv.status, inv.paid_at, inv.amount_received = "paid", now(), received
                    inv.method, inv.admin_note = method, _f("note", 300)
                    lines = pricing.invoice_lines(inv)
                    db.session.add(CreditEntry(
                        family_id=inv.family_id, classes=inv.classes, kind="purchase", amount=received,
                        currency=inv.currency, method=pricing.METHODS.get(method, {}).get("name", method),
                        reference=f"{inv.number} {inv.payer_reference or ''}".strip()[:200],
                        package_id=lines[0].get("package_id") if len(lines) == 1 else None,
                        note=f"Invoice {inv.number}: " + ", ".join(f"{l['child']} {l['plan']}" for l in lines)[:250]))
                    db.session.commit()
                    fam = inv.family
                    mail.send_email(fam.email, f"Payment received: {inv.number}",
                                    f"<p>Assalamu alaikum {html.escape(fam.parent_name)},</p><p>We have received "
                                    f"<b>{pricing.money(received, inv.currency)}</b> for invoice {inv.number}. "
                                    f"<b>{inv.classes} classes</b> have been added to your family's balance.</p>"
                                    "<p>JazakAllahu khairan,<br>Nurul Huda Academy</p>")
            elif action == "cancel" and inv.status in ("pending", "reported"):
                inv.status, inv.admin_note = "cancelled", _f("note", 300) or inv.admin_note
            elif action == "reopen" and inv.status == "cancelled":
                inv.status = "pending"
        elif action == "new_invoice":
            fam = db.session.get(Family, _int("family_id"))
            if fam:
                return redirect(url_for("admin.invoice_new", fid=fam.id))
        if not error:
            db.session.commit()
            return redirect(url_for("admin.payments"))
    waiting = (Invoice.query.filter(Invoice.status.in_(("reported", "pending")))
               .order_by(Invoice.status.desc(), Invoice.created_at.desc()).all())
    done = (Invoice.query.filter(Invoice.status.in_(("paid", "cancelled")))
            .order_by(Invoice.created_at.desc()).limit(50).all())
    methods = {k: {"on": ledger.get_setting(f"pay_{k}_on", "0") == "1", "link": ledger.get_setting(f"pay_{k}_link", ""),
                   "details": ledger.get_setting(f"pay_{k}_details", "")} for k in pricing.METHODS}
    order = (ledger.get_setting("pay_order", "bank,wise,paypal")).split(",")
    return render_template("admin/payments.html", title="Payments", tab="payments", waiting=waiting, done=done,
                           methods=methods, order=order, P=pricing, error=error,
                           families=Family.query.order_by(Family.parent_name).all())


@admin_bp.route("/payments/new/<int:fid>", methods=["GET", "POST"])
@auth.admin_required
def invoice_new(fid):
    """Make an invoice for a family (e.g. after a call), with the same prices and discount rules they would see."""
    from nurulhuda.routes import calculator_input
    fam = db.session.get(Family, fid) or abort(404)
    cur = (request.values.get("cur") or pricing.currencies()[0]).upper()
    kids = fam.students
    choices, months, code = calculator_input(max_children=max(4, len(kids)))
    q = pricing.quote(cur, choices, months, code) if choices else None
    if request.method == "POST":
        _check_form()
        if request.form.get("action") == "create" and q and q.lines and not q.error:
            inv = pricing.make_invoice(fam, q)
            db.session.commit()
            link = url_for("portal.invoice", number=inv.number, _external=True)
            if request.form.get("notify"):
                mail.send_email(fam.email, f"Your invoice {inv.number}: {pricing.money(inv.total, inv.currency)}",
                                f"<p>Assalamu alaikum {html.escape(fam.parent_name)},</p><p>Your invoice <b>{inv.number}</b> "
                                f"is for <b>{pricing.money(inv.total, inv.currency)}</b> ({inv.classes} classes). Please "
                                f"write <b>{inv.number}</b> as the reference when you pay.</p><p>Sign in to see the ways to "
                                f'pay: <a href="{link}">{link}</a></p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>')
            return redirect(url_for("admin.payments"))
    return render_template("admin/invoice_new.html", title=f"Invoice for {fam.parent_name}", tab="payments", fam=fam,
                           kids=kids, P=pricing, cur=cur, plans=pricing.price_list(cur) or
                           Package.query.filter_by(currency=cur, active=True).all(),
                           q=q, months=months, code=code, choices=choices)


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
