"""Noor, the academy's WhatsApp assistant (WhatsApp Business Cloud API + Claude).

- Answers questions in the family's own language from the academy's real information (courses, live prices, policies).
- Collects what is needed for a free trial and creates a TrialRequest (source "whatsapp") in the portal.
- Hands the chat to a person on request, for complaints, payments, or anything it is unsure of, and then stays silent.
- Says it is an AI assistant. Gives no religious rulings, takes no payments or card details, only replies to people
  who message first. Switched off by default (Admin > WhatsApp). Numbers on the mute list are never answered.

Settings (Vercel): WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET, ANTHROPIC_API_KEY.
"""
import hashlib
import hmac
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from flask import current_app

from nurulhuda import books, content as C, db, ledger, mail, pricing
from nurulhuda.models import TrialRequest, WaContact, WaMessage

DAILY_CAP = 40          # bot replies per contact per day
HISTORY = 20            # messages of context sent to Claude
NAME = "Noor"

COUNTRY_CUR = [("971", "AED"), ("44", "GBP"), ("1", "USD"), ("974", "USD"), ("966", "USD"), ("965", "USD"), ("973", "USD"),
               ("968", "USD"), ("92", "USD"), ("91", "USD"), ("880", "USD"), ("20", "USD"), ("60", "USD"), ("62", "USD"),
               ("353", "EUR"), ("33", "EUR"), ("49", "EUR"), ("31", "EUR"), ("32", "EUR"), ("34", "EUR"), ("39", "EUR")]


def now():
    return datetime.now(timezone.utc)


def is_on() -> bool:
    return ledger.get_setting("wa_bot_on", "0") == "1"


def configured() -> dict:
    cfg = current_app.config
    return {"token": bool(cfg.get("WHATSAPP_TOKEN")), "phone_id": bool(cfg.get("WHATSAPP_PHONE_ID")),
            "verify": bool(cfg.get("WHATSAPP_VERIFY_TOKEN")), "secret": bool(cfg.get("WHATSAPP_APP_SECRET")),
            "claude": bool(cfg.get("ANTHROPIC_API_KEY"))}


def currency_for(wa_id: str) -> str:
    for prefix, cur in sorted(COUNTRY_CUR, key=lambda x: -len(x[0])):
        if wa_id.startswith(prefix):
            return cur
    return "USD"


def facts(currency: str) -> str:
    """Everything Noor may say about the academy. Only true, current facts."""
    plans = pricing.price_list(currency) or pricing.price_list("USD")
    cur = currency if pricing.price_list(currency) else "USD"
    plan_lines = "\n".join(f"- {p.name}: {pricing.money(p.price, cur)}"
                           f"{' once' if p.plan in ('starter', 'flexible') else ' per 4 weeks'} ({p.blurb or ''})"
                           for p in plans) or "- Prices: see https://www.nurulhudaacademy.org/pricing"
    courses = "\n".join(f"- {c['name']} ({c.get('age', '')}): {c['text']}" for c in C.PATH)
    alongside = "\n".join(f"- {c['name']}: {c['text']}" for c in C.ALONGSIDE)
    other = ", ".join(c for c in pricing.currencies() if c != cur)
    return f"""ACADEMY FACTS (the only facts you may state)
Nurul Huda Academy: live one-to-one online Quran classes for children (and adults), website https://www.nurulhudaacademy.org.
Founder and Managing Director: Dr. Hayat Ahmad Khan (Dubai). Head of Academics: a Hafiza. Teachers are in Pakistan and Egypt.
Every teacher passes a recitation test before teaching. Female teachers are available on request.
Classes: 30 minutes (hifz 60 minutes), one to one, in the academy's own online classroom with the Quran page on screen.
The same teacher is kept wherever possible; after 6 classes the family can keep the teacher or try another of the same
standard at no charge; a teacher is never changed without telling the family first.
After every class the teacher records where the child reached and what to practise; parents see it on their family page.
Explanations can be in English, Urdu, Arabic, Hindi, Malay, Indonesian, French or Spanish (depending on teachers available).
The first (trial) class is free. The academy replies to trial requests within one working day.
Courses:
{courses}
Alongside:
{alongside}
Prices in {cur} (also available in {other}):
{plan_lines}
Family discounts: {pricing.pct('sibling_2')}% off the second child, {pricing.pct('sibling_3')}% off the third child and each
after; {pricing.pct('upfront_3')}% / {pricing.pct('upfront_6')}% / {pricing.pct('upfront_12')}% off for paying 3 / 6 / 12
months upfront; discounts add up to at most 25%. Families in countries where prices are hard can ask about a community rate.
Payment: after the free trial, the family chooses a plan on their family page and gets an invoice; payment methods are on
the Prices page. Never take payments or card details in WhatsApp.
Policies: a class the teacher misses, or one cancelled at least 12 hours before, is not charged; paid classes stay valid
for 12 months; unused paid classes can be refunded on request; problems with a class can be reported within 48 hours.
Useful links: free trial https://www.nurulhudaacademy.org/free-trial ; prices https://www.nurulhudaacademy.org/pricing ;
free Quran, Qaida and tajweed books https://www.nurulhudaacademy.org/resources ; teachers apply
https://www.nurulhudaacademy.org/teach ; email info@nurulhudaacademy.org"""


RULES = f"""You are {NAME}, the WhatsApp assistant of Nurul Huda Academy. You are an AI assistant, not a person: say so in
your first reply to a new contact and whenever asked. Be warm, brief and respectful, like a kind academy receptionist.
Start a first reply with a greeting such as "Assalamu alaikum". Keep replies short for WhatsApp (usually under 80 words),
plain text, no markdown tables. Always reply in the language the person writes in (Urdu, Arabic, English, Hindi, Malay,
Indonesian, French, Spanish...); for Roman Urdu reply in Roman Urdu.

Your two jobs: (1) answer questions using ONLY the academy facts given; (2) help the family book a free trial by
collecting, naturally over a few messages (not as a form): parent's name, child's first name and age, country (and city),
what they want to learn, teacher preference (female / male / no preference), the language for explanations, days and
times that suit them, and optionally an email address. When you have at least the parent's name, child's age, what to
learn and suitable times, say a teacher will contact them within one working day, and set lead_complete to true.

Never: invent facts, prices, teacher names or availability; give religious rulings or fatwas (say the Head of Academics
will answer and set handover true); give medical, legal or financial advice; ask for or accept card or bank details,
passwords or ID documents; pressure anyone; promise discounts that are not in the facts; discuss donations.
If a child seems to be writing, be gentle and ask them to have a parent message us.
Set handover to true when the person asks for a human, complains, asks about an existing payment, refund or a class
problem, is upset, asks something the facts do not cover, or anything sensitive; your reply should then say a member of
the team will reply here soon.
If the message is abusive or clearly spam, reply politely once and set handover true.

Reply ONLY with one JSON object and nothing else:
{{"reply": "<your WhatsApp message>", "language": "<ISO code you replied in>",
 "lead": {{"parent_name": "", "student_name": "", "student_age": "", "country": "", "city": "", "course": "",
          "teacher_gender": "", "instruction_language": "", "preferred_times": "", "email": "", "notes": ""}},
 "lead_complete": false, "handover": false, "handover_reason": ""}}
In "lead", fill every field you have learned so far in the whole conversation (English values), leave the rest empty."""


def ask_claude(currency: str, history: list[dict]) -> dict:
    """history: [{"role": "user"|"assistant", "content": str}, ...] ending with the user's message."""
    key = current_app.config.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    msgs = []
    for m in history[-HISTORY:]:
        if msgs and msgs[-1]["role"] == m["role"]:
            msgs[-1]["content"] += "\n" + m["content"]
        else:
            msgs.append({"role": m["role"], "content": m["content"][:2000]})
    if not msgs or msgs[0]["role"] != "user":
        msgs.insert(0, {"role": "user", "content": "(conversation start)"})
    msgs.append({"role": "assistant", "content": "{"})
    body = {"model": current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 700,
            "system": RULES + "\n\n" + facts(currency), "messages": msgs}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read())
    text = "{" + "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return parse(text)


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    if not isinstance(out, dict) or not str(out.get("reply", "")).strip():
        clean = re.sub(r"[{}\"]", "", text).strip()
        out = {"reply": clean[:800] or "Assalamu alaikum! A member of our team will reply here soon.", "handover": not clean}
    out["reply"] = str(out["reply"]).strip()[:1500]
    out["lead"] = out.get("lead") if isinstance(out.get("lead"), dict) else {}
    out["lead_complete"] = bool(out.get("lead_complete"))
    out["handover"] = bool(out.get("handover"))
    return out


def send_text(wa_id: str, body: str) -> str | None:
    """Send a WhatsApp text; returns the WhatsApp message id or None."""
    cfg = current_app.config
    if not (cfg.get("WHATSAPP_TOKEN") and cfg.get("WHATSAPP_PHONE_ID")):
        current_app.logger.info("WhatsApp not configured; not sent to %s", wa_id[-4:])
        return None
    url = f"https://graph.facebook.com/{cfg.get('WHATSAPP_API_VERSION', 'v23.0')}/{cfg['WHATSAPP_PHONE_ID']}/messages"
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": wa_id, "type": "text",
               "text": {"preview_url": True, "body": body[:4000]}}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {cfg['WHATSAPP_TOKEN']}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return (data.get("messages") or [{}])[0].get("id")
    except urllib.error.HTTPError as e:
        current_app.logger.error("WhatsApp send failed (HTTP %s): %s", e.code, e.read()[:300])
    except Exception:
        current_app.logger.exception("WhatsApp send failed")
    return None


def valid_signature(raw: bytes, header: str | None) -> bool:
    secret = current_app.config.get("WHATSAPP_APP_SECRET")
    if not secret:
        return True           # not configured yet: accept (set WHATSAPP_APP_SECRET before going live)
    if not header or not header.startswith("sha256="):
        return False
    good = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header[7:], good)


def history_of(contact: WaContact) -> list[dict]:
    rows = (WaMessage.query.filter_by(contact_id=contact.id).order_by(WaMessage.id.desc()).limit(HISTORY).all())[::-1]
    return [{"role": "user" if r.direction == "in" else "assistant", "content": r.body} for r in rows]


def _replies_today(contact: WaContact) -> int:
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return WaMessage.query.filter(WaMessage.contact_id == contact.id, WaMessage.direction == "bot",
                                  WaMessage.created_at >= start).count()


def _merge_lead(contact: WaContact, lead: dict) -> dict:
    old = json.loads(contact.lead_json or "{}")
    for k, v in (lead or {}).items():
        if isinstance(v, (str, int)) and str(v).strip():
            old[k] = str(v).strip()[:200]
    contact.lead_json = json.dumps(old, ensure_ascii=False)
    return old


def _create_trial(contact: WaContact, lead: dict) -> TrialRequest:
    email = lead.get("email", "")
    t = TrialRequest(parent_name=(lead.get("parent_name") or contact.profile_name or "WhatsApp contact")[:120],
                     email=email[:200] if "@" in email else None, phone="+" + contact.wa_id,
                     country=lead.get("country", "")[:60] or None, city=lead.get("city", "")[:80] or None,
                     student_name=lead.get("student_name", "")[:120] or None, student_age=lead.get("student_age", "")[:20] or None,
                     course=lead.get("course", "")[:60] or None, teacher_gender=lead.get("teacher_gender", "")[:20] or None,
                     preferred_times=lead.get("preferred_times", "")[:200] or None,
                     instruction_language=lead.get("instruction_language", "")[:40] or None,
                     notes=("From WhatsApp. " + lead.get("notes", ""))[:2000], site_lang=(contact.lang or "en")[:5],
                     source="whatsapp")
    db.session.add(t)
    db.session.flush()
    contact.trial_request_id = t.id
    books.log("whatsapp_trial_created", "trial_request", t.id)
    return t


def _notify(subject: str, contact: WaContact, extra: str = "") -> None:
    import html as _h
    rows = (WaMessage.query.filter_by(contact_id=contact.id).order_by(WaMessage.id.desc()).limit(12).all())[::-1]
    convo = "".join(f"<p><b>{'Family' if r.direction == 'in' else ('Noor' if r.direction == 'bot' else 'Team')}:</b> "
                    f"{_h.escape(r.body)}</p>" for r in rows)
    mail.send_email(current_app.config.get("NOTIFY_EMAIL"), subject,
                    f"<p>WhatsApp: +{_h.escape(contact.wa_id)} ({_h.escape(contact.profile_name or 'no name')})</p>{extra}"
                    f"<hr>{convo}<p>Reply from WhatsApp, or in Admin &gt; WhatsApp.</p>")


def handle_inbound(wa_id: str, profile_name: str, text: str, msg_id: str, kind: str = "text") -> str | None:
    """Store an incoming message and, if allowed, reply. Returns the reply text (or None)."""
    if msg_id and WaMessage.query.filter_by(wa_message_id=msg_id).first():
        return None                                            # WhatsApp retry: already handled
    contact = WaContact.query.filter_by(wa_id=wa_id).first()
    if not contact:
        contact = WaContact(wa_id=wa_id, profile_name=(profile_name or "")[:120], status="bot")
        db.session.add(contact)
        db.session.flush()
    elif profile_name and not contact.profile_name:
        contact.profile_name = profile_name[:120]
    body = text if kind == "text" else f"[{kind} message]"
    db.session.add(WaMessage(contact_id=contact.id, direction="in", body=body[:4000], wa_message_id=msg_id or None))
    contact.last_at = now()
    db.session.commit()

    if not is_on() or contact.status in ("muted", "human"):
        if contact.status == "human":
            _notify(f"WhatsApp: new message from {contact.profile_name or wa_id}", contact)
        return None
    if _replies_today(contact) >= DAILY_CAP:
        return None
    if kind != "text":
        reply = ("Assalamu alaikum! I'm Noor, the academy's AI assistant. I can only read typed messages; please type "
                 "your question and I'll help.")
        result = {"reply": reply, "lead": {}, "handover": False, "lead_complete": False}
    else:
        try:
            result = ask_claude(currency_for(wa_id), history_of(contact))
        except Exception:
            current_app.logger.exception("Noor could not answer")
            result = {"reply": "Assalamu alaikum! Thank you for your message. A member of our team will reply here soon.",
                      "lead": {}, "handover": True, "lead_complete": False, "handover_reason": "assistant error"}
    lead = _merge_lead(contact, result.get("lead"))
    if result.get("language"):
        contact.lang = str(result["language"])[:5]
    sent_id = send_text(wa_id, result["reply"])
    db.session.add(WaMessage(contact_id=contact.id, direction="bot", body=result["reply"], wa_message_id=sent_id))
    if result.get("lead_complete") and not contact.trial_request_id:
        t = _create_trial(contact, lead)
        db.session.commit()
        _notify(f"New free trial request from WhatsApp: {t.parent_name}", contact,
                f"<p>Trial request #{t.id} was created in Sign-ups.</p>")
    if result.get("handover"):
        contact.status, contact.human_since = "human", now()
        books.log("whatsapp_handover", "wa_contact", contact.id, reason=str(result.get("handover_reason", ""))[:200])
        db.session.commit()
        _notify(f"WhatsApp: {contact.profile_name or wa_id} needs a person", contact,
                f"<p>Reason: {result.get('handover_reason') or 'asked for a person'}</p>")
    db.session.commit()
    return result["reply"]


def staff_reply(contact: WaContact, body: str) -> bool:
    """Send a message typed by the team in Admin (only within 24 hours of the family's last message)."""
    last_in = (WaMessage.query.filter_by(contact_id=contact.id, direction="in").order_by(WaMessage.id.desc()).first())
    if not last_in or (now() - (last_in.created_at if last_in.created_at.tzinfo else last_in.created_at.replace(tzinfo=timezone.utc))) > timedelta(hours=24):
        return False
    sent = send_text(contact.wa_id, body)
    db.session.add(WaMessage(contact_id=contact.id, direction="staff", body=body[:4000], wa_message_id=sent))
    books.log("whatsapp_staff_reply", "wa_contact", contact.id)
    db.session.commit()
    return bool(sent)


def try_chat(history: list[dict], wa_id: str = "971500000000") -> dict:
    """Admin 'Try Noor' box: no database writes, nothing sent."""
    return ask_claude(currency_for(wa_id), history)

