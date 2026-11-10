import hmac
import secrets

from flask import (Blueprint, g, Response, abort, current_app, redirect, render_template, request, send_from_directory,
                   session, url_for)

from nurulhuda import content as C
from nurulhuda import db, mail
from nurulhuda.models import DawahRequest, TeacherApplication, TrialRequest

site_bp = Blueprint("site", __name__)

PAGES = ["site.home", "site.courses", "site.families", "site.trial", "site.teach", "site.about", "site.videos",
         "site.contact", "site.terms", "site.vision", "site.islam", "site.app"]


@site_bp.app_context_processor
def _inject():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return {"C": C, "site_url": current_app.config["SITE_URL"].rstrip("/"), "csrf": session["csrf"],
            "contact_email": current_app.config["CONTACT_EMAIL"], "admin_email": current_app.config["ADMIN_EMAIL"]}


def _check_form():
    if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
        abort(400, "This form expired. Please go back, refresh the page and send it again.")
    return not request.form.get("website")  # hidden field: bots fill it, people do not


def _f(name, limit=200):
    return (request.form.get(name) or "").strip()[:limit]


def _save(row) -> bool:
    try:
        db.session.add(row)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not save %s", type(row).__name__)
        return False


def _save_failed(template, page, title, form):
    msg = ("We could not save your details just now. Please try again in a minute, or e-mail us at "
           + current_app.config["CONTACT_EMAIL"] + ".")
    return render_template(template, page=page, title=title, errors={"_save": msg}, form=form), 503


@site_bp.route("/")
def home():
    return render_template("home.html", page="home")


@site_bp.route("/courses")
def courses():
    return render_template("courses.html", page="courses", title="Courses")


def _languages(with_arabic=False):
    """The language questions on the forms, as stored on the record."""
    from flask import g
    parts = []
    for n in (1, 2, 3):
        name, level = _f(f"lang{n}", 40), _f(f"lang{n}_level", 20)
        if name and name in C.LANGUAGE_CHOICES and f"{name} (" not in "; ".join(parts):
            parts.append(f"{name} ({level if level in C.LEVELS else 'Native'})")
    out = {"language_profile": "; ".join(parts)[:500] or None,
           "english_level": _f("english_level", 20) if _f("english_level") in C.LEVELS_WITH_NONE else None,
           "urdu_level": _f("urdu_level", 20) if _f("urdu_level") in C.LEVELS_WITH_NONE else None,
           "site_lang": getattr(g, "lang", "en")}
    if with_arabic:
        out["arabic_level"] = _f("arabic_level", 20) if _f("arabic_level") in C.LEVELS_WITH_NONE else None
    return out


@site_bp.route("/families")
def families():
    return render_template("families.html", page="families", title="For families")


@site_bp.route("/free-trial", methods=["GET", "POST"])
def trial():
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        if not _check_form():
            return redirect(url_for("site.thanks", kind="trial"))
        for key, label in [("parent_name", "your name"), ("email", "your e-mail")]:
            if not _f(key):
                errors[key] = f"Enter {label}."
        if _f("email") and "@" not in _f("email"):
            errors["email"] = "Enter an e-mail address like name@example.com."
        if not errors:
            t = TrialRequest(parent_name=_f("parent_name", 120), email=_f("email"), phone=_f("phone", 40),
                             country=_f("country", 60), city=_f("city", 80), student_name=_f("student_name", 120),
                             student_age=_f("student_age", 20), course=_f("course", 60),
                             teacher_gender=_f("teacher_gender", 20), preferred_times=_f("preferred_times"),
                             notes=_f("notes", 2000), instruction_language=_f("instruction_language", 40),
                             **_languages())
            if not _save(t):
                return _save_failed("trial.html", "families", "Book a free trial class", form)
            mail.trial_emails(t)
            return redirect(url_for("site.thanks", kind="trial"))
    return render_template("trial.html", page="families", title="Book a free trial class", errors=errors, form=form)


@site_bp.route("/teach", methods=["GET", "POST"])
def teach():
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        if not _check_form():
            return redirect(url_for("site.thanks", kind="teacher"))
        for key, label in [("full_name", "your full name"), ("email", "your e-mail"), ("country", "your country")]:
            if not _f(key):
                errors[key] = f"Enter {label}."
        if _f("email") and "@" not in _f("email"):
            errors["email"] = "Enter an e-mail address like name@example.com."
        if not request.form.getlist("levels"):
            errors["levels"] = "Choose at least one level you can teach."
        if not errors:
            a = TeacherApplication(full_name=_f("full_name", 120), email=_f("email"), phone=_f("phone", 40),
                                   country=_f("country", 60), gender=_f("gender", 20),
                                   levels=", ".join(request.form.getlist("levels"))[:200],
                                   qualifications=_f("qualifications", 3000),
                                   experience_years=_f("experience_years", 20),
                                   hours=_f("hours"), recitation_link=_f("recitation_link", 300),
                                   **_languages(with_arabic=True))
            if not _save(a):
                return _save_failed("teach.html", "teach", "Teach with us", form)
            mail.teacher_emails(a)
            return redirect(url_for("site.thanks", kind="teacher"))
    return render_template("teach.html", page="teach", title="Teach with us", errors=errors, form=form)


@site_bp.route("/thanks/<kind>")
def thanks(kind):
    if kind not in ("trial", "teacher", "islam"):
        abort(404)
    return render_template("thanks.html", kind=kind, title="Thank you")


@site_bp.route("/about")
def about():
    return render_template("about.html", page="about", title="About us")


@site_bp.route("/vision")
def vision():
    return render_template("vision.html", page="vision", title="Our vision")


@site_bp.route("/discover-islam", methods=["GET", "POST"])
def islam():
    errors, form = {}, {}
    if request.method == "POST":
        form = request.form
        if not _check_form():
            return redirect(url_for("site.thanks", kind="islam"))
        for key, label in [("name", "your name"), ("email", "your e-mail")]:
            if not _f(key):
                errors[key] = f"Enter {label}."
        if _f("email") and "@" not in _f("email"):
            errors["email"] = "Enter an e-mail address like name@example.com."
        if not errors:
            d = DawahRequest(name=_f("name", 120), email=_f("email"), phone=_f("phone", 40), country=_f("country", 60),
                             interest=_f("interest", 80), teacher_gender=_f("teacher_gender", 20),
                             message=_f("message", 3000), site_lang=getattr(g, "lang", "en"))
            if not _save(d):
                return _save_failed("islam.html", "islam", "Discover Islam", form)
            mail.dawah_emails(d)
            return redirect(url_for("site.thanks", kind="islam"))
    return render_template("islam.html", page="islam", title="Discover Islam", errors=errors, form=form)


@site_bp.route("/videos")
def videos():
    return render_template("videos.html", page="videos", title="Short videos")


@site_bp.route("/contact")
def contact():
    return render_template("contact.html", page="contact", title="Contact")


@site_bp.route("/terms")
def terms():
    return render_template("terms.html", title="Terms and privacy")


# --- sign-ups list for the founders ---------------------------------------------
@site_bp.route("/admin", methods=["GET", "POST"])
def admin():
    password = current_app.config.get("ADMIN_PASSWORD")
    if not password:
        abort(404)
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), password):
            session["admin"] = True
        else:
            return render_template("admin_login.html", title="Sign in", error="That password is not right."), 401
    if not session.get("admin"):
        return render_template("admin_login.html", title="Sign in")
    trials = TrialRequest.query.order_by(TrialRequest.created_at.desc()).limit(500).all()
    teachers = TeacherApplication.query.order_by(TeacherApplication.created_at.desc()).limit(500).all()
    dawah = DawahRequest.query.order_by(DawahRequest.created_at.desc()).limit(500).all()
    return render_template("admin.html", title="Sign-ups", tab="signups", trials=trials, teachers=teachers, dawah=dawah)


@site_bp.route("/admin/sign-out")
def admin_sign_out():
    session.pop("admin", None)
    return redirect(url_for("site.home"))


@site_bp.after_app_request
def _private(resp):
    if request.path.startswith(("/admin", "/thanks")):
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        resp.headers["Cache-Control"] = "no-store"
    return resp


@site_bp.route("/robots.txt")
def robots():
    base = current_app.config["SITE_URL"].rstrip("/")
    return Response(f"User-agent: *\nAllow: /\nDisallow: /admin\n\nSitemap: {base}/sitemap.xml\n", mimetype="text/plain")


@site_bp.route("/sitemap.xml")
def sitemap():
    base = current_app.config["SITE_URL"].rstrip("/")
    rows = "".join(f"<url><loc>{base}{url_for(ep)}</loc></url>" for ep in PAGES)
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f"{rows}</urlset>", mimetype="application/xml")


@site_bp.route("/app")
def app():
    return render_template("app.html", page="app", title="Get the app")


@site_bp.route("/offline")
def offline():
    return render_template("offline.html", title="Offline")


@site_bp.route("/sw.js")
def service_worker():
    # Served from the site root so it can look after every page.
    resp = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript", max_age=0)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@site_bp.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json", max_age=3600)


@site_bp.route("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder + "/icons", "favicon-32.png", mimetype="image/png", max_age=86400)


@site_bp.route("/health")
def health():
    return {"ok": True}
