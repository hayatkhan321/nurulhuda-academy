"""E-mail through Resend, the same way hayatclinics.com sends its newsletter."""
import html
import json
import urllib.error
import urllib.request

from flask import current_app


def send_email(to: str, subject: str, inner_html: str) -> bool:
    key = current_app.config.get("RESEND_API_KEY")
    if not key or not to:
        current_app.logger.info("E-mail not sent (RESEND_API_KEY or recipient missing): %s", subject)
        return False
    payload = {"from": current_app.config["MAIL_FROM"], "to": [to], "subject": subject, "html": _wrap(inner_html)}
    if current_app.config.get("MAIL_REPLY_TO"):
        payload["reply_to"] = current_app.config["MAIL_REPLY_TO"]
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "nurulhuda/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        current_app.logger.error("Resend refused %r (HTTP %s): %s", subject, exc.code, exc.read()[:400])
    except Exception as exc:
        current_app.logger.error("E-mail %r failed: %s", subject, exc)
    return False


def _wrap(inner: str) -> str:
    return (
        '<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.6;color:#13241f;max-width:560px;margin:0 auto">'
        '<p style="font-size:22px;color:#0b5d45;margin:0 0 4px"><b>Nurul Huda Academy</b></p>'
        f'<p style="font-size:20px;color:#c98a1c;margin:0 0 20px" dir="rtl">نور الهدى</p>{inner}'
        '<p style="color:#5c6f68;font-size:13px;margin-top:32px">Nurul Huda Academy &middot; nurulhudaacademy.org</p></div>'
    )


def _rows(pairs) -> str:
    cells = "".join(
        f'<tr><td style="padding:4px 12px 4px 0;color:#5c6f68">{html.escape(k)}</td><td style="padding:4px 0">{html.escape(str(v or "-"))}</td></tr>'
        for k, v in pairs
    )
    return f'<table style="border-collapse:collapse">{cells}</table>'


def trial_emails(t) -> None:
    send_email(
        current_app.config.get("NOTIFY_EMAIL"), f"New free trial request: {t.parent_name} ({t.country or 'country not given'})",
        "<p>A family has asked for a free trial class.</p>" + _rows([
            ("Parent", t.parent_name), ("E-mail", t.email), ("Phone / WhatsApp", t.phone), ("Country", t.country),
            ("City", t.city), ("Student", t.student_name), ("Age", t.student_age), ("Course", t.course),
            ("Teacher", t.teacher_gender), ("Preferred times", t.preferred_times), ("Notes", t.notes)]),
    )
    send_email(
        t.email, "We have your free trial request",
        f"<p>Assalamu alaikum {html.escape(t.parent_name)},</p>"
        "<p>Thank you for asking for a free trial class. Within one working day we will contact you to agree a time, "
        "and match you with a teacher who suits your child's level and your time zone.</p>"
        "<p>If you have a question in the meantime, simply reply to this e-mail.</p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>",
    )


def teacher_emails(a) -> None:
    send_email(
        current_app.config.get("NOTIFY_EMAIL"), f"New teacher application: {a.full_name} ({a.country or 'country not given'})",
        "<p>A teacher has applied to teach.</p>" + _rows([
            ("Name", a.full_name), ("E-mail", a.email), ("Phone / WhatsApp", a.phone), ("Country", a.country),
            ("Gender", a.gender), ("Levels", a.levels), ("Years teaching", a.experience_years),
            ("Languages", a.languages), ("Available hours", a.hours), ("Recitation link", a.recitation_link),
            ("Qualifications", a.qualifications)]),
    )
    send_email(
        a.email, "We have your teacher application",
        f"<p>Assalamu alaikum {html.escape(a.full_name)},</p>"
        "<p>Thank you for applying to teach with Nurul Huda Academy. Our Head of Academics reviews every application personally. "
        "If you have not yet sent a recitation recording, please reply to this e-mail with a link to one (2 to 3 minutes of any surah).</p>"
        "<p>We aim to reply within five working days.</p><p>JazakAllahu khairan,<br>Nurul Huda Academy</p>",
    )


def dawah_emails(d) -> None:
    send_email(
        current_app.config.get("NOTIFY_EMAIL"), f"Discover Islam request: {d.name} ({d.interest or 'not stated'})",
        "<p>Someone has asked for a free class on Islam.</p>" + _rows([
            ("Name", d.name), ("E-mail", d.email), ("Phone / WhatsApp", d.phone), ("Country", d.country),
            ("About them", d.interest), ("Teacher", d.teacher_gender), ("Message", d.message)]),
    )
    send_email(
        d.email, "Your free class on Islam",
        f"<p>Dear {html.escape(d.name)},</p>"
        "<p>Thank you for getting in touch. A teacher will contact you within one working day to arrange a private, "
        "one-to-one conversation at a time that suits you. There is no cost and no pressure: ask anything you like.</p>"
        "<p>With warm regards,<br>Nurul Huda Academy</p>",
    )
