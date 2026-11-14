"""Claude as the academy's bookkeeping reviewer.

Claude only reads a snapshot of the books and writes a review or an answer for the founders. It cannot change
any record or move money. It needs ANTHROPIC_API_KEY (from console.anthropic.com) in the website settings.
"""
import json
import urllib.error
import urllib.request
from datetime import timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import func

from nurulhuda import books, db
from nurulhuda.ledger import now
from nurulhuda.models import CreditEntry, Expense, Family, Payout, Teacher, TeacherEarning

SYSTEM = """You are the bookkeeping reviewer for Nurul Huda Academy, an online Quran academy registered in the UAE.
Families pay the academy for packages of classes; teachers (mostly in Pakistan and Egypt) are paid per class taught.
You receive a snapshot of the academy's books as JSON. Rules:
- Use only the figures in the snapshot. Never invent or estimate a number. If something is not in the snapshot, say so.
- Amounts in AED are the accounting currency; other currencies are shown as received.
- Point out anything an auditor would question: mismatches, missing references or AED values, negative balances,
  unpaid or held teacher pay, unusual refunds or corrections, months left open, unmarked classes.
- You cannot change records or move money. Recommend actions for the founders to take in the admin area.
- Write in plain, short English for a busy founder. Use short headings and bullet points. No jargon.
- You are not a licensed accountant or tax adviser; for tax filing, say an accountant should confirm."""


def configured() -> bool:
    return bool(current_app.config.get("ANTHROPIC_API_KEY"))


def _d(v):
    return str(v) if isinstance(v, Decimal) else v


def snapshot(ym: str | None = None) -> dict:
    ym = ym or f"{now():%Y-%m}"
    y, m = map(int, ym.split("-"))
    prev = f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"
    since = now() - timedelta(days=62)
    fams = {f.id: f.parent_name for f in Family.query.all()}
    names = {t.id: t.full_name for t in Teacher.query.all()}
    bal = dict(db.session.query(CreditEntry.family_id, func.sum(CreditEntry.classes)).group_by(CreditEntry.family_id).all())
    owed = {}
    for e in TeacherEarning.query.filter(TeacherEarning.status.in_(("owed", "held"))).all():
        k = (names.get(e.teacher_id, "?"), e.currency, e.status)
        owed[k] = owed.get(k, Decimal("0")) + Decimal(e.amount)
    summ = lambda s: {k: ({kk: _d(vv) for kk, vv in v.items()} if isinstance(v, dict) else _d(v)) for k, v in s.items()}
    return {
        "today": f"{now():%Y-%m-%d}",
        "books_closed_through": books.closed_through() or "nothing closed yet",
        "this_month": summ(books.summary(ym)),
        "previous_month": summ(books.summary(prev)),
        "automatic_checks": books.checks(),
        "family_class_balances": {fams.get(k, k): int(v or 0) for k, v in bal.items()},
        "teacher_pay_not_yet_paid": [{"teacher": k[0], "currency": k[1], "status": k[2], "amount": str(v)} for k, v in owed.items()],
        "money_last_two_months": [
            {"date": f"{e.created_at:%Y-%m-%d}", "number": e.receipt_no, "type": books.KIND_LABELS.get(e.kind, e.kind),
             "family": fams.get(e.family_id), "amount": _d(e.amount), "currency": e.currency, "aed": _d(e.amount_aed),
             "reference": e.reference, "note": e.note}
            for e in CreditEntry.query.filter(CreditEntry.amount.isnot(None), CreditEntry.created_at >= since)
            .order_by(CreditEntry.created_at).limit(400).all()] +
            [{"date": f"{p.created_at:%Y-%m-%d}", "number": p.voucher_no, "type": "Teacher payout", "teacher": names.get(p.teacher_id),
              "amount": _d(p.amount), "currency": p.currency, "aed": _d(p.amount_aed), "reference": p.reference}
             for p in Payout.query.filter(Payout.created_at >= since).order_by(Payout.created_at).limit(200).all()] +
            [{"date": f"{x.spent_on}", "number": x.voucher_no, "type": f"Expense: {x.category}", "payee": x.payee,
              "amount": _d(x.amount), "currency": x.currency, "aed": _d(x.amount_aed), "description": x.description}
             for x in Expense.query.filter(Expense.spent_on >= since.date()).order_by(Expense.spent_on).limit(200).all()],
    }


def ask(question: str, ym: str | None = None) -> str:
    """Send the snapshot and a question to Claude; return the answer text, or a plain error message."""
    key = current_app.config.get("ANTHROPIC_API_KEY")
    if not key:
        return "Claude is not switched on yet. Add ANTHROPIC_API_KEY in the website settings."
    body = {
        "model": current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        "max_tokens": 1500,
        "system": SYSTEM,
        "messages": [{"role": "user", "content":
                      "Snapshot of the books:\n" + json.dumps(snapshot(ym), ensure_ascii=False, default=str) +
                      "\n\nQuestion from the founder:\n" + question[:2000]}],
    }
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=50) as r:
            data = json.loads(r.read())
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip() or "No answer came back."
    except urllib.error.HTTPError as e:
        current_app.logger.warning("Claude API error %s: %s", e.code, e.read()[:300])
        return f"Claude could not answer just now (error {e.code}). Check the API key and credit balance, then try again."
    except Exception:
        current_app.logger.exception("Claude API call failed")
        return "Claude could not be reached just now. Please try again in a minute."


MONTHLY_QUESTION = ("Review this month and last month like an auditor would. Give: 1) a three-line summary in AED, "
                    "2) anything that needs fixing, most important first, with exactly what to do in the admin area, "
                    "3) anything that looks unusual, 4) whether last month is ready to be closed.")
