"""Founders' tools: families, teachers, packages, scheduling, payments received, problems and teacher payouts."""
import csv
import html
import io
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for

from nurulhuda import content as C
from nurulhuda import auth, books, db, ledger, mail, pricing
from nurulhuda.ledger import now
from nurulhuda.models import (AuditLog, ClassReview, ClassSession, CreditEntry, Expense, Family, Invoice, Package, Payout, PromoCode, Student, Teacher, TeacherCheckin,
                              TeacherApplication, TeacherEarning, TrialRequest)
from nurulhuda.routes import _check_form, _f
from nurulhuda.timefmt import ZONES, fmt, parse_local, tz

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
CURRENCIES = ["USD", "GBP", "EUR", "CAD", "AED", "PKR", "EGP"]


@admin_bp.app_context_processor
def _admin_ctx():
    def rate_map():
        return {c: (str(books.last_rate(c)) if books.last_rate(c) is not None else "") for c in CURRENCIES}
    return {"ZONES": ZONES, "CURRENCIES": CURRENCIES, "last_rate": books.last_rate, "KIND_LABELS": books.KIND_LABELS,
            "rate_map": rate_map}


def _rate(currency):
    """The AED rate typed on the form (1 for AED)."""
    if currency == "AED":
        return Decimal("1")
    try:
        r = Decimal(_f("aed_rate", 20))
        return r if r > 0 else None
    except InvalidOperation:
        return None


def _receipt_email(fam, e):
    link = url_for("portal.receipt", eid=e.id, _external=True)
    mail.send_email(fam.email, f"Receipt {e.receipt_no}: Nurul Huda Academy",
                    f"<p>Assalamu alaikum {html.escape(fam.parent_name)},</p>"
                    f"<p>Thank you. We have received <b>{e.amount} {e.currency}</b> for {html.escape(e.note or 'classes')} "
                    f"({e.classes} classes have been added to your balance).</p>"
                    f'<p>Receipt number: <b>{e.receipt_no}</b>. You can view and print it at <a href="{link}">{link}</a> '
                    "after signing in.</p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>")


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
            fam.teacher_pref = trial.teacher_pref or "same"
        books.log("family_created", "family", fam.id, name=fam.parent_name, email=fam.email)
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
        error = None
        if action == "student" and _f("first_name"):
            st = Student(family_id=fam.id, first_name=_f("first_name", 80), age=_f("age", 20),
                         course=_f("course", 60), level=_f("level", 120))
            db.session.add(st)
            books.log("student_added", "family", fam.id, name=st.first_name)
        elif action == "payment":
            pkg = db.session.get(Package, _int("package_id"))
            amount, cur = _money("amount"), _f("currency", 3) or (pkg.currency if pkg else "USD")
            rate = _rate(cur)
            if not (pkg and amount and amount > 0 and rate):
                error = "Choose a package and enter the amount received and the AED rate."
            else:
                e = CreditEntry(family_id=fam.id, classes=pkg.classes, kind="purchase", amount=amount, currency=cur,
                                method=_f("method", 40), reference=_f("reference", 200), package_id=pkg.id, note=pkg.name,
                                receipt_no=books.next_number("RC"), aed_rate=rate, amount_aed=books.to_aed(amount, rate))
                db.session.add(e)
                books.remember_rate(cur, rate)
                db.session.flush()
                books.log("payment_received", "credit_entry", e.id, family=fam.parent_name, receipt=e.receipt_no,
                          amount=amount, currency=cur, aed=e.amount_aed, classes=pkg.classes, reference=e.reference)
                db.session.commit()
                _receipt_email(fam, e)
        elif action == "adjust" and _int("classes"):
            e = CreditEntry(family_id=fam.id, classes=_int("classes"), kind="adjustment",
                            note=_f("note", 300) or "Manual adjustment")
            db.session.add(e)
            db.session.flush()
            books.log("classes_adjusted", "credit_entry", e.id, family=fam.parent_name, classes=e.classes, note=e.note)
        elif action == "refund":
            amount, cur = _money("amount"), _f("currency", 3) or "USD"
            rate = _rate(cur)
            if not (amount and amount > 0 and rate):
                error = "Enter the amount refunded and the AED rate."
            else:
                e = CreditEntry(family_id=fam.id, classes=-abs(_int("classes")), kind="refund", amount=-amount,
                                currency=cur, method=_f("method", 40), reference=_f("reference", 200),
                                note=_f("note", 300) or "Refund", receipt_no=books.next_number("RF"),
                                aed_rate=rate, amount_aed=books.to_aed(-amount, rate))
                db.session.add(e)
                books.remember_rate(cur, rate)
                db.session.flush()
                books.log("refund_paid", "credit_entry", e.id, family=fam.parent_name, receipt=e.receipt_no,
                          amount=-amount, currency=cur, aed=e.amount_aed, classes=e.classes, reference=e.reference)
        elif action == "reverse":
            orig = db.session.get(CreditEntry, _int("entry_id"))
            reason = _f("reason", 200)
            if not (orig and orig.family_id == fam.id and orig.kind in ("purchase", "refund", "adjustment") and reason):
                error = "Choose the entry to correct and give a reason."
            elif CreditEntry.query.filter_by(reverses_id=orig.id).first():
                error = "That entry has already been corrected."
            else:
                e = CreditEntry(family_id=fam.id, classes=-orig.classes, kind="reversal",
                                amount=-orig.amount if orig.amount is not None else None, currency=orig.currency,
                                method=orig.method, reference=orig.reference, reverses_id=orig.id,
                                note=f"Correction of {orig.receipt_no or 'entry ' + str(orig.id)}: {reason}"[:300],
                                receipt_no=books.next_number("CN") if orig.amount is not None else None,
                                aed_rate=orig.aed_rate,
                                amount_aed=-orig.amount_aed if orig.amount_aed is not None else None)
                db.session.add(e)
                db.session.flush()
                books.log("entry_corrected", "credit_entry", e.id, corrects=orig.receipt_no or orig.id, reason=reason,
                          amount=e.amount, currency=e.currency, classes=e.classes)
        elif action == "details":
            before = {"phone": fam.phone, "country": fam.country, "timezone": fam.timezone}
            fam.phone, fam.country = _f("phone", 40), _f("country", 60)
            fam.timezone = _f("timezone", 60) or fam.timezone
            fam.recording_consent = bool(request.form.get("recording_consent"))
            fam.notes = _f("notes", 3000)
            books.log("family_details_changed", "family", fam.id, before=before,
                      after={"phone": fam.phone, "country": fam.country, "timezone": fam.timezone})
        if error:
            db.session.rollback()
            return redirect(url_for("admin.family", fid=fam.id, error=error))
        db.session.commit()
        return redirect(url_for("admin.family", fid=fam.id))
    sids = [s.id for s in fam.students] or [0]
    classes = ClassSession.query.filter(ClassSession.student_id.in_(sids)).order_by(ClassSession.starts_at.desc()).limit(50).all()
    entries = CreditEntry.query.filter_by(family_id=fam.id).order_by(CreditEntry.created_at.desc()).all()
    corrected = {e.reverses_id for e in entries if e.reverses_id}
    return render_template("admin/family.html", title=fam.parent_name, tab="families", fam=fam, classes=classes,
                           entries=entries, balance=ledger.balance(fam.id), corrected=corrected,
                           error=request.args.get("error"),
                           packages=Package.query.filter_by(active=True).order_by(Package.classes).all())


# --- teachers -------------------------------------------------------------------------------------
@admin_bp.route("/teachers", methods=["GET", "POST"])
@auth.admin_required
def teachers():
    error = None
    if request.method == "POST":
        _check_form()
        if request.form.get("action") == "limit":
            books.log("teacher_limit_changed", None, None, before=ledger.teacher_limit(), after=max(1, _int("limit", 5)))
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
                books.log("teacher_activated" if t.active else "teacher_paused", "teacher", t.id, name=t.full_name)
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
        before = {"rate": t.rate, "currency": t.rate_currency, "payout": t.payout_method} if t else None
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
        db.session.flush()
        books.log("teacher_saved", "teacher", t.id, name=t.full_name, before=before,
                  after={"rate": t.rate, "currency": t.rate_currency, "payout": t.payout_method})
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
            books.log("package_toggled", "package", p.id, name=p.name, active=p.active)
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
                db.session.flush()
                books.log("package_saved", "package", p.id, name=p.name, classes=p.classes, price=p.price, currency=p.currency)
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


# --- quality: class ratings and teacher comparison ----------------------------------------------------
@admin_bp.route("/quality", methods=["GET", "POST"])
@auth.admin_required
def quality():
    from datetime import timedelta
    if request.method == "POST":
        _check_form()
        c = db.session.get(TeacherCheckin, _int("checkin_id")) or abort(404)
        c.handled = True
        db.session.commit()
        return redirect(url_for("admin.quality"))
    days = _int("days") if request.args.get("days") else 90
    days = days if days in (30, 90, 365) else 90
    since = now() - timedelta(days=days)
    reviews = ClassReview.query.filter(ClassReview.created_at >= since).all()
    classes = ClassSession.query.filter(ClassSession.starts_at >= since, ClassSession.starts_at <= now()).all()
    checkins = TeacherCheckin.query.filter(TeacherCheckin.created_at >= since).all()
    rows = []
    for t in Teacher.query.order_by(Teacher.full_name).all():
        mine = [c for c in classes if c.teacher_id == t.id]
        rv = [r for r in reviews if r.teacher_id == t.id]
        ck = [c for c in checkins if c.teacher_id == t.id]
        done = sum(1 for c in mine if c.status == "completed")
        t_missed = sum(1 for c in mine if c.status == "teacher_missed")
        s_missed = sum(1 for c in mine if c.status == "student_missed")
        with_progress = sum(1 for c in mine if c.status == "completed" and c.prog_book)
        measured = [c for c in mine if c.status == "completed" and c.t_secs]
        due = sum((c.minutes or 30) * 60 for c in measured)
        if not mine and not rv:
            continue
        rows.append({"t": t, "done": done, "t_missed": t_missed, "s_missed": s_missed,
                     "reliability": round(done / (done + t_missed) * 100) if done + t_missed else None,
                     "avg": round(sum(r.stars for r in rv) / len(rv), 2) if rv else None, "n": len(rv),
                     "five": round(sum(1 for r in rv if r.stars == 5) / len(rv) * 100) if rv else None,
                     "rated": round(len(rv) / done * 100) if done else None,
                     "keep": sum(1 for c in ck if c.choice == "keep"), "change": sum(1 for c in ck if c.choice == "change"),
                     "reports": round(with_progress / done * 100) if done else None,
                     "present": min(100, round(sum(c.t_secs for c in measured) / due * 100)) if due else None,
                     "view": min(100, round(sum(c.t_view_secs for c in measured) / due * 100)) if due else None,
                     "cam": min(100, round(sum(c.t_cam_secs for c in measured) / due * 100)) if due else None})
    rows.sort(key=lambda r: (r["avg"] is None, -(r["avg"] or 0), -r["n"]))
    overall = {"avg": round(sum(r.stars for r in reviews) / len(reviews), 2) if reviews else None, "n": len(reviews),
               "happy": round(sum(1 for r in reviews if r.stars >= 4) / len(reviews) * 100) if reviews else None,
               "dist": [sum(1 for r in reviews if r.stars == n) for n in range(5, 0, -1)],
               "keep": sum(1 for c in checkins if c.choice == "keep"), "change": sum(1 for c in checkins if c.choice == "change")}
    open_changes = TeacherCheckin.query.filter_by(choice="change", handled=False).order_by(TeacherCheckin.created_at).all()
    comments = (ClassReview.query.filter(ClassReview.comment.isnot(None), ClassReview.comment != "")
                .order_by(ClassReview.created_at.desc()).limit(30).all())
    return render_template("admin/quality.html", title="Quality", tab="quality", rows=rows, overall=overall,
                           open_changes=open_changes, comments=comments, days=days)


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
                rate = _rate(inv.currency)
                if received is None or received <= 0:
                    error = f"Enter the amount you received for {inv.number}."
                elif rate is None:
                    error = f"Enter today's AED rate for {inv.currency} so the books show {inv.number} in dirhams."
                elif books.is_closed(now()):
                    error = "This month's books are closed. Reopen them on the Books page first."
                else:
                    method = _f("method", 20) or inv.method or "bank"
                    inv.status, inv.paid_at, inv.amount_received = "paid", now(), received
                    inv.method, inv.admin_note = method, _f("note", 300)
                    lines = pricing.invoice_lines(inv)
                    books.remember_rate(inv.currency, rate)
                    entry = CreditEntry(
                        family_id=inv.family_id, classes=inv.classes, kind="purchase", amount=received,
                        currency=inv.currency, method=pricing.METHODS.get(method, {}).get("name", method),
                        reference=f"{inv.number} {inv.payer_reference or ''}".strip()[:200],
                        package_id=lines[0].get("package_id") if len(lines) == 1 else None,
                        note=f"Invoice {inv.number}: " + ", ".join(f"{l['child']} {l['plan']}" for l in lines)[:250],
                        receipt_no=books.next_number("RC"), aed_rate=rate,
                        amount_aed=(received * rate).quantize(Decimal("0.01")))
                    db.session.add(entry)
                    db.session.flush()
                    books.log("payment_received", "invoice", inv.id, number=inv.number, receipt=entry.receipt_no,
                              amount=str(received), currency=inv.currency, aed=str(entry.amount_aed), method=method)
                    db.session.commit()
                    _receipt_email(inv.family, entry)

            elif action == "cancel" and inv.status in ("pending", "reported"):
                inv.status, inv.admin_note = "cancelled", _f("note", 300) or inv.admin_note
                books.log("invoice_cancelled", "invoice", inv.id, number=inv.number)
            elif action == "reopen" and inv.status == "cancelled":
                inv.status = "pending"
                books.log("invoice_reopened", "invoice", inv.id, number=inv.number)
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
                db.session.flush()
                books.log("classes_scheduled", "student", st.id, teacher=t.full_name, count=len(made),
                          first=min((c.starts_at for c in made), default=None))
                db.session.commit()
                made.sort(key=lambda c: c.starts_at)
                if request.form.get("notify"):
                    _notify_scheduled(made)
                return redirect(url_for("admin.classes"))
        elif action in ("status", "cancel"):
            cs = db.session.get(ClassSession, _int("class_id")) or abort(404)
            new = "cancelled" if action == "cancel" else _f("status", 20)
            if books.is_closed(cs.starts_at):
                error = (f"The books for {cs.starts_at:%B %Y} are closed, so this class cannot change. "
                         "Record a correction on the family's page instead.")
            elif new in ledger.STATUS_LABELS:
                books.log("class_status_changed", "class", cs.id, before=cs.status, after=new)
                ledger.set_status(cs, new)
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
        if decision in ("pay", "refund") and not books.is_closed(cs.starts_at):
            books.log("problem_resolved", "class", cs.id, decision=decision, note=_f("note", 180))
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
        rate = _rate(t.rate_currency)
        if rows and rate:
            total = sum((r.amount for r in rows), Decimal("0"))
            p = Payout(teacher_id=t.id, amount=total, currency=t.rate_currency, method=_f("method", 40),
                       reference=_f("reference", 200), voucher_no=books.next_number("PV"), aed_rate=rate,
                       amount_aed=books.to_aed(total, rate))
            db.session.add(p)
            books.remember_rate(t.rate_currency, rate)
            db.session.flush()
            for r in rows:
                r.status, r.payout_id = "paid", p.id
            books.log("teacher_paid", "payout", p.id, teacher=t.full_name, voucher=p.voucher_no, amount=total,
                      currency=p.currency, aed=p.amount_aed, classes=len(rows), reference=p.reference)
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


# --- books ----------------------------------------------------------------------------------------
@admin_bp.route("/books", methods=["GET", "POST"])
@auth.admin_required
def books_home():
    error = None
    if request.method == "POST":
        _check_form()
        if request.form.get("action") == "close":
            ym = books.next_month_to_close()
            start, end = books.month_bounds(ym)
            if end > now():
                error = f"{start:%B %Y} has not finished yet."
            elif ClassSession.query.filter(ClassSession.starts_at >= start, ClassSession.starts_at < end,
                                           ClassSession.status == "scheduled").count():
                error = f"Some classes in {start:%B %Y} are still unmarked. Mark them before closing the month."
            else:
                ledger.set_setting("books_closed_through", ym)
                books.log("month_closed", None, None, month=ym, summary={k: str(v) for k, v in books.summary(ym).items()
                                                                         if k.endswith("_aed")})
                db.session.commit()
                return redirect(url_for("admin.books_home", ym=ym))
        elif request.form.get("action") == "business":
            ledger.set_setting("business_details", _f("business_details", 500))
            books.log("business_details_changed", None, None)
            db.session.commit()
            return redirect(url_for("admin.books_home"))
    return books_home_render(ym=request.args.get("ym"), error=error)


def books_home_render(ym=None, error=None, question=None, answer=None):
    from nurulhuda import books_ai
    ym = ym or f"{now():%Y-%m}"
    try:
        sm = books.summary(ym)
    except ValueError:
        abort(404)
    y, m = map(int, ym.split("-"))
    prev_ym = f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"
    next_ym = f"{y + (m == 12)}-{m % 12 + 1:02d}"
    return render_template("admin/books.html", title="Books", tab="books", s=sm, checks=books.checks(), error=error,
                           closed=books.closed_through(), to_close=books.next_month_to_close(), prev_ym=prev_ym,
                           next_ym=next_ym, business=ledger.get_setting("business_details", ""),
                           recent=AuditLog.query.order_by(AuditLog.id.desc()).limit(15).all(),
                           ai_on=books_ai.configured(), question=question, answer=answer)


@admin_bp.route("/books/ask", methods=["POST"])
@auth.admin_required
def books_ask():
    from nurulhuda import books_ai
    _check_form()
    q = _f("question", 2000) or books_ai.MONTHLY_QUESTION
    ym = _f("ym", 7) or None
    answer = books_ai.ask(q, ym)
    books.log("books_question_asked", None, None, question=q[:300])
    db.session.commit()
    return books_home_render(ym=ym, question=q, answer=answer)


@admin_bp.route("/expenses", methods=["GET", "POST"])
@auth.admin_required
def expenses():
    error = None
    if request.method == "POST":
        _check_form()
        from datetime import date as _date
        if request.form.get("action") == "reverse":
            orig = db.session.get(Expense, _int("expense_id")) or abort(404)
            reason = _f("reason", 200)
            if not reason or Expense.query.filter_by(reverses_id=orig.id).first() or orig.reverses_id:
                error = "Give a reason. An expense can be corrected only once."
            else:
                x = Expense(spent_on=now().date(), category=orig.category, description=f"Correction of {orig.voucher_no}: {reason}"[:300],
                            payee=orig.payee, amount=-orig.amount, currency=orig.currency, aed_rate=orig.aed_rate,
                            amount_aed=-orig.amount_aed, method=orig.method, reference=orig.reference,
                            voucher_no=books.next_number("EX"), reverses_id=orig.id)
                db.session.add(x)
                db.session.flush()
                books.log("expense_corrected", "expense", x.id, corrects=orig.voucher_no, reason=reason)
                db.session.commit()
                return redirect(url_for("admin.expenses"))
        else:
            amount, cur = _money("amount"), _f("currency", 3) or "AED"
            rate = _rate(cur)
            try:
                spent_on = _date.fromisoformat(_f("spent_on", 10))
            except ValueError:
                spent_on = None
            if not (amount and amount > 0 and rate and spent_on and _f("description") and _f("category") in books.EXPENSE_CATEGORIES):
                error = "Enter the date, category, what it was for, the amount and the AED rate."
            elif books.is_closed(spent_on):
                error = f"The books for {spent_on:%B %Y} are closed. Date the expense in an open month."
            elif spent_on > now().date():
                error = "The date cannot be in the future."
            else:
                x = Expense(spent_on=spent_on, category=_f("category", 40), description=_f("description", 300),
                            payee=_f("payee", 120), amount=amount, currency=cur, aed_rate=rate,
                            amount_aed=books.to_aed(amount, rate), method=_f("method", 40), reference=_f("reference", 200),
                            voucher_no=books.next_number("EX"))
                db.session.add(x)
                books.remember_rate(cur, rate)
                db.session.flush()
                books.log("expense_recorded", "expense", x.id, voucher=x.voucher_no, amount=amount, currency=cur,
                          aed=x.amount_aed, category=x.category, payee=x.payee)
                db.session.commit()
                return redirect(url_for("admin.expenses"))
    rows = Expense.query.order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(200).all()
    corrected = {x.reverses_id for x in rows if x.reverses_id}
    return render_template("admin/expenses.html", title="Expenses", tab="books", rows=rows, error=error,
                           categories=books.EXPENSE_CATEGORIES, corrected=corrected, today=now().date())


@admin_bp.route("/receipts/<int:eid>")
@auth.admin_required
def receipt(eid):
    e = db.session.get(CreditEntry, eid) or abort(404)
    if not e.receipt_no:
        abort(404)
    return render_template("receipt.html", e=e, fam=e.family_obj, business=ledger.get_setting("business_details", ""))


def _csv(rows, header):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _period():
    from datetime import date as _date, datetime as _dt
    try:
        start = _date.fromisoformat(request.args.get("from", ""))
    except ValueError:
        start = _date(now().year, 1, 1)
    try:
        end = _date.fromisoformat(request.args.get("to", ""))
    except ValueError:
        end = now().date()
    to_dt = lambda d: _dt(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, end, to_dt(start), to_dt(end) + timedelta(days=1)


def _journal(s_dt, e_dt, s_d, e_d):
    """Every money movement, oldest first, with the dirham value."""
    fams = {f.id: f.parent_name for f in Family.query.all()}
    names = {t.id: t.full_name for t in Teacher.query.all()}
    out = []
    for e in CreditEntry.query.filter(CreditEntry.amount.isnot(None), CreditEntry.created_at >= s_dt,
                                      CreditEntry.created_at < e_dt).all():
        out.append((e.created_at, e.receipt_no or "", books.KIND_LABELS.get(e.kind, e.kind), fams.get(e.family_id, ""),
                    e.note or "", f"{e.amount:.2f}", e.currency, f"{e.aed_rate or ''}", f"{e.amount_aed if e.amount_aed is not None else ''}",
                    e.method or "", e.reference or ""))
    for p in Payout.query.filter(Payout.created_at >= s_dt, Payout.created_at < e_dt).all():
        out.append((p.created_at, p.voucher_no or "", "Teacher payout", names.get(p.teacher_id, ""), "Classes taught",
                    f"{-p.amount:.2f}", p.currency, f"{p.aed_rate or ''}", f"{-p.amount_aed if p.amount_aed is not None else ''}",
                    p.method or "", p.reference or ""))
    for x in Expense.query.filter(Expense.spent_on >= s_d, Expense.spent_on <= e_d).all():
        when = datetime.combine(x.spent_on, datetime.min.time(), tzinfo=timezone.utc)
        out.append((when, x.voucher_no, f"Expense: {x.category}", x.payee or "", x.description, f"{-x.amount:.2f}",
                    x.currency, f"{x.aed_rate}", f"{-x.amount_aed}", x.method or "", x.reference or ""))
    out.sort(key=lambda r: (books_aware(r[0]), r[1]))
    return [(f"{books_aware(r[0]):%Y-%m-%d %H:%M}",) + r[1:] for r in out]


def books_aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


JOURNAL_HEADER = ["Date (UTC)", "Number", "Type", "Family / teacher / payee", "Details", "Amount", "Currency",
                  "AED rate", "Amount in AED", "Method", "Bank or card reference"]


@admin_bp.route("/books/journal.csv")
@auth.admin_required
def journal_csv():
    s_d, e_d, s_dt, e_dt = _period()
    return Response(_csv(_journal(s_dt, e_dt, s_d, e_d), JOURNAL_HEADER), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=nurulhuda-journal-{s_d}-to-{e_d}.csv"})


@admin_bp.route("/books/audit-pack.zip")
@auth.admin_required
def audit_pack():
    """Everything an auditor asks for, for a period, in one file."""
    import json as _json
    import zipfile
    s_d, e_d, s_dt, e_dt = _period()
    fams = {f.id: f.parent_name for f in Family.query.all()}
    names = {t.id: t.full_name for t in Teacher.query.all()}
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("1-journal-all-money.csv", _csv(_journal(s_dt, e_dt, s_d, e_d), JOURNAL_HEADER))
        z.writestr("2-family-class-balances.csv", _csv(
            [(fams.get(e.family_id, ""), f"{books_aware(e.created_at):%Y-%m-%d %H:%M}", books.KIND_LABELS.get(e.kind, e.kind),
              e.classes, e.receipt_no or "", e.class_id or "", e.note or "")
             for e in CreditEntry.query.filter(CreditEntry.created_at >= s_dt, CreditEntry.created_at < e_dt)
             .order_by(CreditEntry.created_at).all()],
            ["Family", "Date (UTC)", "Type", "Classes", "Receipt", "Class id", "Note"]))
        z.writestr("3-classes.csv", _csv(
            [(c.id, f"{books_aware(c.starts_at):%Y-%m-%d %H:%M}", c.minutes, c.student.first_name, fams.get(c.student.family_id, ""),
              c.teacher.full_name, c.status, (c.teacher_note or "").replace("\n", " "), c.flag_reason or "", c.flag_resolution or "")
             for c in ClassSession.query.filter(ClassSession.starts_at >= s_dt, ClassSession.starts_at < e_dt)
             .order_by(ClassSession.starts_at).all()],
            ["Class id", "Starts (UTC)", "Minutes", "Student", "Family", "Teacher", "Status", "Teacher's note",
             "Parent report", "Decision"]))
        z.writestr("4-teacher-earnings.csv", _csv(
            [(e.id, names.get(e.teacher_id, ""), e.class_id, f"{e.amount:.2f}", e.currency, e.status, e.payout_id or "")
             for e in TeacherEarning.query.filter(TeacherEarning.created_at >= s_dt, TeacherEarning.created_at < e_dt).all()],
            ["Earning id", "Teacher", "Class id", "Amount", "Currency", "Status", "Payout id"]))
        z.writestr("5-teacher-payouts.csv", _csv(
            [(p.voucher_no or p.id, f"{books_aware(p.created_at):%Y-%m-%d %H:%M}", names.get(p.teacher_id, ""), f"{p.amount:.2f}",
              p.currency, p.aed_rate or "", p.amount_aed or "", p.method or "", p.reference or "",
              TeacherEarning.query.filter_by(payout_id=p.id).count())
             for p in Payout.query.filter(Payout.created_at >= s_dt, Payout.created_at < e_dt).order_by(Payout.created_at).all()],
            ["Voucher", "Date (UTC)", "Teacher", "Amount", "Currency", "AED rate", "Amount in AED", "Method", "Reference",
             "Classes covered"]))
        z.writestr("6-expenses.csv", _csv(
            [(x.voucher_no, x.spent_on, x.category, x.description, x.payee or "", f"{x.amount:.2f}", x.currency, x.aed_rate,
              x.amount_aed, x.method or "", x.reference or "", x.reverses_id or "")
             for x in Expense.query.filter(Expense.spent_on >= s_d, Expense.spent_on <= e_d).order_by(Expense.spent_on).all()],
            ["Voucher", "Date", "Category", "Description", "Payee", "Amount", "Currency", "AED rate", "Amount in AED",
             "Method", "Reference", "Corrects"]))
        z.writestr("7-activity-log.csv", _csv(
            [(a.id, f"{books_aware(a.created_at):%Y-%m-%d %H:%M:%S}", a.actor, a.ip or "", a.action, a.entity or "",
              a.entity_id or "", a.details or "")
             for a in AuditLog.query.filter(AuditLog.created_at >= s_dt, AuditLog.created_at < e_dt).order_by(AuditLog.id).all()],
            ["Id", "Time (UTC)", "Who", "IP address", "Action", "Record", "Record id", "Details"]))
        months, cur = [], s_d.replace(day=1)
        while cur <= e_d:
            sm = books.summary(f"{cur:%Y-%m}")
            months.append((sm["label"], sm["payments"], sm["income_aed"], sm["refunds_aed"], sm["payouts_aed"],
                           sm["expenses_aed"], sm["net_aed"], sm["classes"]["completed"], sm["classes"]["student_missed"]))
            cur = cur.replace(year=cur.year + (cur.month == 12), month=cur.month % 12 + 1)
        z.writestr("0-monthly-summary-AED.csv", _csv(months, ["Month", "Payments", "Income AED", "Refunds AED",
                                                              "Teacher pay AED", "Expenses AED", "Net AED",
                                                              "Classes completed", "Student absent (charged)"]))
        problems = books.checks()
        z.writestr("README.txt",
                   f"Nurul Huda Academy: audit pack\nPeriod: {s_d} to {e_d}\nPrepared: {now():%Y-%m-%d %H:%M} UTC\n"
                   f"Books closed through: {books.closed_through() or 'not yet closed'}\n\n"
                   "Records are append-only: nothing is edited or deleted, mistakes are corrected with numbered entries\n"
                   "(CN- for families, EX- corrections for expenses) that point at the original.\n"
                   "Numbers: RC- receipts, RF- refunds, CN- credit notes, PV- teacher payout vouchers, EX- expenses.\n\n"
                   f"Open issues found by the automatic checks: {sum(p['count'] for p in problems)}\n" +
                   "".join(f"- {p['title']}: {p['count']}\n" for p in problems))
    books.log("audit_pack_downloaded", None, None, period=f"{s_d} to {e_d}")
    db.session.commit()
    return Response(mem.getvalue(), mimetype="application/zip",
                    headers={"Content-Disposition": f"attachment; filename=nurulhuda-audit-pack-{s_d}-to-{e_d}.zip"})
