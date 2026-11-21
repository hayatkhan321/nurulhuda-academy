"""Admin sections added in November 2026: Classroom (activity reports and backgrounds), Conduct, Memberships
(prices, benefits, teacher levels and language checks) and Education support. Same admin login as admin.py."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from flask import abort, redirect, render_template, request, url_for

from nurulhuda import auth, books, classroom, db, ledger, mail, memberships as M, pricing, support
from nurulhuda import content as C
from nurulhuda.admin import _int, _money, _rate, _receipt_email, admin_bp
from nurulhuda.ledger import now
from nurulhuda.models import ClassSession, ConductReport, SponsorPurchase, SupportApplication, Teacher
from nurulhuda.routes import _check_form, _f


# --- classroom: activity reports and backgrounds ---------------------------------------------------------------
@admin_bp.route("/classroom", methods=["GET", "POST"], endpoint="classroom")
@auth.admin_required
def classroom_page():
    saved = None
    if request.method == "POST":
        _check_form()
        mode = request.form.get("mode")
        image = request.form.get("image")
        url = _f("custom_url", 300)
        if mode in classroom.BG_MODES:
            ledger.set_setting("classroom_bg_mode", mode)
        if image in classroom.BACKGROUNDS:
            ledger.set_setting("classroom_bg_image", image)
        ledger.set_setting("classroom_bg_url", url if url.startswith("https://") else "")
        try:
            ledger.set_setting("classroom_blur_strength", str(max(0.1, min(1.0, float(request.form.get("strength") or 0.8)))))
        except ValueError:
            pass
        books.log("classroom_background_changed", None, None, mode=mode, image=image, custom=bool(url))
        db.session.commit()
        saved = "Saved. New classes open with these settings."
    days = 14
    rows = (ClassSession.query.filter(ClassSession.starts_at >= now() - timedelta(days=days), ClassSession.starts_at <= now() + timedelta(hours=2))
            .order_by(ClassSession.starts_at.desc()).limit(200).all())
    review = classroom.summary_counts([c.id for c in rows])
    return render_template("admin/classroom.html", title="Classroom", tab="classroom", rows=rows, review=review,
                           bg=classroom.background(), BG_MODES=classroom.BG_MODES, BACKGROUNDS=classroom.BACKGROUNDS,
                           custom=ledger.get_setting("classroom_bg_url", ""),
                           image=ledger.get_setting("classroom_bg_image", "academy-green"), saved=saved, days=days)


@admin_bp.route("/classes/<int:cid>/activity")
@auth.admin_required
def class_activity(cid):
    cs = db.session.get(ClassSession, cid) or abort(404)
    return render_template("class_activity.html", title="Class activity", cs=cs, r=classroom.report(cs),
                           zone="Asia/Dubai", viewer="admin", hm=classroom.clock("Asia/Dubai"))


# --- conduct ---------------------------------------------------------------------------------------------------
CONDUCT_STATUS = {"open": "New", "looking": "Being looked into", "upheld": "Upheld", "not_upheld": "Not upheld"}


@admin_bp.route("/conduct", methods=["GET", "POST"])
@auth.admin_required
def conduct():
    if request.method == "POST":
        _check_form()
        r = db.session.get(ConductReport, _int("report_id")) or abort(404)
        status = request.form.get("status")
        if status in CONDUCT_STATUS:
            note = _f("note", 2000)
            stamp = f"[{now():%d %b %Y}] {CONDUCT_STATUS[status]}" + (f": {note}" if note else "")
            r.admin_notes = ((r.admin_notes + "\n") if r.admin_notes else "") + stamp
            r.status = status
            r.closed_at = now() if status in ("upheld", "not_upheld") else None
            books.log("conduct_report_updated", "conduct_report", r.id, status=status)
            if request.form.get("pause") and r.teacher.active:
                r.teacher.active = False
                books.log("teacher_paused", "teacher", r.teacher.id, name=r.teacher.full_name, reason=f"conduct report {r.id}")
            db.session.commit()
        return redirect(url_for("admin.conduct"))
    reports = ConductReport.query.order_by(ConductReport.closed_at.isnot(None), ConductReport.created_at.desc()).limit(200).all()
    teachers = Teacher.query.order_by(Teacher.active.desc(), Teacher.full_name).all()
    return render_template("admin/conduct.html", title="Conduct", tab="conduct", reports=reports, teachers=teachers,
                           C=C, CONDUCT_STATUS=CONDUCT_STATUS)


# --- memberships, teacher levels and language checks ----------------------------------------------------------
@admin_bp.route("/memberships", methods=["GET", "POST"])
@auth.admin_required
def memberships():
    error = saved = None
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "tiers":
            ledger.set_setting("memberships_on", "1" if request.form.get("memberships_on") else "0")
            for tier in M.TIERS:
                for field in M.FIELDS:
                    key = f"{tier}_{field}"
                    if field == "need_verified":
                        val = "1" if request.form.get(key) else "0"
                    else:
                        val = (request.form.get(key) or "").strip()[:480]
                        if field not in ("label", "benefits", "offer_label"):
                            try:
                                Decimal(val or "0")
                            except InvalidOperation:
                                error = f"{M.config(tier)['label']}: '{val}' is not a number."
                                break
                    ledger.set_setting(f"tier_{tier}_{field}", val)
            ledger.set_setting("match_min_level", request.form.get("match_min_level") if request.form.get("match_min_level") in C.LEVELS else "Fluent")
            ledger.set_setting("match_need_verified", "1" if request.form.get("match_need_verified") else "0")
            if not error:
                books.log("memberships_changed", None, None, on=M.on())
                saved = "Saved."
        elif action == "teacher":
            t = db.session.get(Teacher, _int("teacher_id")) or abort(404)
            before = {"tier": t.tier, "verified": t.qualifications_verified, "years": t.experience_years,
                      "english": t.english_verified, "urdu": t.urdu_verified, "arabic": t.arabic_verified}
            t.qualifications_verified = bool(request.form.get("qualifications_verified"))
            t.experience_years = max(0, min(60, _int("experience_years"))) if request.form.get("experience_years") else None
            t.english_verified = bool(request.form.get("english_verified"))
            t.urdu_verified = bool(request.form.get("urdu_verified"))
            t.arabic_verified = bool(request.form.get("arabic_verified"))
            t.lang_note = _f("lang_note", 200) or None
            tier = request.form.get("tier")
            if tier in M.TIERS and tier != t.tier:
                db.session.flush()
                if tier != "standard" and not M.eligibility(t)[tier]["ok"]:
                    error = (f"{t.full_name} does not yet clear the bar for {M.config(tier)['label']}. "
                             "See the checklist; the other changes were saved.")
                else:
                    t.tier = tier
            books.log("teacher_level_changed", "teacher", t.id, before=before,
                      after={"tier": t.tier, "verified": t.qualifications_verified, "years": t.experience_years,
                             "english": t.english_verified, "urdu": t.urdu_verified, "arabic": t.arabic_verified})
            saved = f"{t.full_name} saved."
        db.session.commit()
    teachers = Teacher.query.order_by(Teacher.active.desc(), Teacher.full_name).all()
    rows = []
    for t in teachers:
        s = M.teacher_stats(t)
        rows.append({"t": t, "s": s, "elig": M.eligibility(t, s)})
    return render_template("admin/memberships.html", title="Memberships", tab="memberships", M=M, C=C, rows=rows,
                           error=error, saved=saved, cfg={t: M.config(t) for t in M.TIERS},
                           raw={t: {f: M.setting(t, f) for f in M.FIELDS} for t in M.TIERS},
                           cur=pricing.currencies()[0], P=pricing)


# --- education support -----------------------------------------------------------------------------------------
@admin_bp.route("/support", methods=["GET", "POST"])
@auth.admin_required
def support_home():
    error = saved = None
    if request.method == "POST":
        _check_form()
        action = request.form.get("action")
        if action == "settings":
            ledger.set_setting("support_on", "1" if request.form.get("support_on") else "0")
            ledger.set_setting("support_name", _f("support_name", 120) or support.DEFAULTS["support_name"])
            ledger.set_setting("support_who", "all" if request.form.get("support_who") == "all" else "diamond")
            for key in ("support_lessons_per_child", "support_packs", "support_coin_prices", "support_max_asked"):
                ledger.set_setting(key, _f(key, 300) or support.DEFAULTS[key])
            books.log("support_settings_changed", None, None, on=support.on())
            saved = "Saved."
        elif action in ("confirm", "cancel"):
            p = db.session.get(SponsorPurchase, _int("purchase_id")) or abort(404)
            if action == "cancel" and p.status in ("pending", "reported"):
                p.status = "cancelled"
                books.log("sponsor_purchase_cancelled", "sponsor_purchase", p.id, number=p.number)
            elif action == "confirm" and p.status in ("pending", "reported"):
                received, rate = _money("amount_received"), _rate(p.currency)
                if received is None or received <= 0:
                    error = f"Enter the amount you received for {p.number}."
                elif rate is None:
                    error = f"Enter today's AED rate for {p.currency}."
                elif books.is_closed(now()):
                    error = "This month's books are closed. Reopen them on the Books page first."
                else:
                    method = pricing.METHODS.get(_f("method", 20) or p.method or "bank", {}).get("name", "Bank transfer")
                    entry = support.confirm(p, received, rate, method, _f("note", 200))
                    db.session.commit()
                    _receipt_email(p.family, entry)
        elif action == "decide":
            app = db.session.get(SupportApplication, _int("application_id")) or abort(404)
            approve = request.form.get("decision") == "approve"
            if not support.decide(app, approve, _int("lessons"), _f("note", 500)):
                error = "That application has already been decided."
            else:
                db.session.flush()
                mail.send_email(app.family.email, "Your application for sponsored lessons",
                                "<p>Assalamu alaikum,</p>" + (
                                    f"<p>Your application for {app.student.first_name} has been approved for "
                                    f"<b>{app.lessons_approved} lessons</b>. They will appear on your page as sponsored lessons.</p>"
                                    if approve else
                                    "<p>Thank you for applying. We are not able to offer sponsored lessons this time. "
                                    "You are welcome to apply again later.</p>") + "<p>Nurul Huda Academy</p>")
        elif action == "allocate":
            app = db.session.get(SupportApplication, _int("application_id")) or abort(404)
            got, error = support.allocate(app, _int("coins"))
            if got:
                saved = f"{got} sponsored lessons given to {app.student.first_name}."
        elif action == "close":
            app = db.session.get(SupportApplication, _int("application_id")) or abort(404)
            if app.status == "approved":
                app.status = "closed"
                books.log("support_closed", "support_application", app.id)
        elif action == "promo" and _int("coins") > 0:
            support.add_promo(_int("coins"), _f("note", 300))
        if error:
            db.session.rollback()
        else:
            db.session.commit()
    rep = support.report()
    waiting = (SponsorPurchase.query.filter(SponsorPurchase.status.in_(("pending", "reported")))
               .order_by(SponsorPurchase.status.desc(), SponsorPurchase.created_at.desc()).all())
    paid = SponsorPurchase.query.filter_by(status="paid").order_by(SponsorPurchase.paid_at.desc()).limit(50).all()
    apps = SupportApplication.query.order_by(SupportApplication.status != "pending", SupportApplication.created_at.desc()).limit(200).all()
    donors = {}
    for p in SponsorPurchase.query.filter_by(status="paid").all():
        d = donors.setdefault(p.family_id, {"family": p.family, "bought": 0})
        d["bought"] += p.coins
    for fid, d in donors.items():
        d.update(support.donor_view(d["family"]))
    return render_template("admin/support.html", title="Education support", tab="support", S=support, rep=rep,
                           waiting=waiting, paid=paid, apps=apps, donors=list(donors.values()), P=pricing,
                           error=error, saved=saved, raw={k: support.setting(k) for k in support.DEFAULTS})
