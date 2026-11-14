"""Keeping the books audit-ready.

- Money records are never edited or deleted. A mistake is corrected with a reversing entry that points at it.
- Every payment gets a receipt number (RC-2026-0001), every refund RF-..., every teacher payout PV-...,
  every expense EX-...; numbers run in order, per year, with no gaps.
- Every amount is also kept in AED at the rate of the day, so the yearly accounts can be drawn up in dirhams.
- Every change made by the founders, teachers or families is written to the activity log.
- When a month is closed, nothing dated in it can change any more.
"""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from flask import has_request_context, request, session
from sqlalchemy import func

from nurulhuda import db
from nurulhuda.models import (AuditLog, ClassSession, CreditEntry, Expense, Family, Payout, Setting, Teacher,
                              TeacherEarning)

EXPENSE_CATEGORIES = ["Teaching platform (video)", "Website and hosting", "Licence and government fees", "Bank and payment fees",
                      "Salaries and contractors", "Marketing", "Books and materials", "Accounting and legal",
                      "Office and equipment", "Other"]
KIND_LABELS = {"purchase": "Payment", "used": "Class used", "returned": "Class returned", "adjustment": "Adjustment",
               "refund": "Refund", "reversal": "Correction"}


# --- activity log ---------------------------------------------------------------------------------
def actor() -> str:
    if not has_request_context():
        return "system"
    if session.get("admin"):
        return "admin"
    role, uid = session.get("role"), session.get("uid")
    return f"{role}:{uid}" if role and uid else "visitor"


def log(action: str, entity: str | None = None, entity_id: int | None = None, **details) -> None:
    ip = None
    if has_request_context():
        ip = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()[:64]
    clean = {k: (str(v) if isinstance(v, (Decimal, date, datetime)) else v) for k, v in details.items() if v is not None}
    db.session.add(AuditLog(actor=actor(), ip=ip, action=action, entity=entity, entity_id=entity_id,
                            details=json.dumps(clean, ensure_ascii=False) if clean else None))


# --- numbering ------------------------------------------------------------------------------------
def next_number(prefix: str) -> str:
    """RC-2026-0001 style numbers, in order with no gaps, safe when two people save at once."""
    year = datetime.now(timezone.utc).year
    key = f"seq:{prefix}-{year}"
    row = db.session.query(Setting).filter_by(key=key).with_for_update().first()
    n = int(row.value) + 1 if row else 1
    if row:
        row.value = str(n)
    else:
        db.session.add(Setting(key=key, value=str(n)))
    db.session.flush()
    return f"{prefix}-{year}-{n:04d}"


# --- dirhams --------------------------------------------------------------------------------------
def last_rate(currency: str) -> Decimal | None:
    if currency == "AED":
        return Decimal("1")
    row = db.session.get(Setting, f"rate:{currency}")
    return Decimal(row.value) if row else None


def remember_rate(currency: str, rate: Decimal) -> None:
    if currency != "AED":
        row = db.session.get(Setting, f"rate:{currency}")
        if row:
            row.value = str(rate)
        else:
            db.session.add(Setting(key=f"rate:{currency}", value=str(rate)))


def to_aed(amount, rate) -> Decimal | None:
    if amount is None or rate is None:
        return None
    return (Decimal(amount) * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- closing months -------------------------------------------------------------------------------
def closed_through() -> str:
    """'2026-10' means October 2026 and everything before it is closed. Empty if nothing is closed."""
    row = db.session.get(Setting, "books_closed_through")
    return row.value if row else ""


def is_closed(when) -> bool:
    if when is None:
        return False
    if isinstance(when, datetime):
        when = (when if when.tzinfo else when.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()
    ct = closed_through()
    return bool(ct) and f"{when:%Y-%m}" <= ct


def month_bounds(ym: str):
    y, m = map(int, ym.split("-"))
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=timezone.utc)
    return start, end


def next_month_to_close() -> str:
    """The month after the last closed one, or the month of the first record."""
    ct = closed_through()
    if ct:
        y, m = map(int, ct.split("-"))
        return f"{y + (m == 12)}-{(m % 12) + 1:02d}"
    firsts = [db.session.query(func.min(CreditEntry.created_at)).scalar(),
              db.session.query(func.min(Payout.created_at)).scalar(),
              db.session.query(func.min(ClassSession.starts_at)).scalar()]
    firsts = [f for f in firsts if f]
    first = min(firsts) if firsts else datetime.now(timezone.utc)
    return f"{first:%Y-%m}"


# --- the month in figures -------------------------------------------------------------------------
def _sum_by_currency(rows, amount_attr="amount"):
    out = {}
    for r in rows:
        out[r.currency] = out.get(r.currency, Decimal("0")) + Decimal(getattr(r, amount_attr) or 0)
    return out


def summary(ym: str) -> dict:
    start, end = month_bounds(ym)
    money = CreditEntry.query.filter(CreditEntry.created_at >= start, CreditEntry.created_at < end,
                                     CreditEntry.amount.isnot(None)).all()
    def origin(e):
        """What a correction corrects: a reversal of a payment counts as (negative) income."""
        while e is not None and e.kind == "reversal" and e.reverses_id:
            e = db.session.get(CreditEntry, e.reverses_id)
        return e.kind if e is not None else None
    income = [e for e in money if origin(e) == "purchase"]
    refunds = [e for e in money if origin(e) == "refund"]
    payouts = Payout.query.filter(Payout.created_at >= start, Payout.created_at < end).all()
    expenses = Expense.query.filter(Expense.spent_on >= start.date(), Expense.spent_on < end.date()).all()
    classes = ClassSession.query.filter(ClassSession.starts_at >= start, ClassSession.starts_at < end).all()
    aed = lambda rows: sum((Decimal(r.amount_aed or 0) for r in rows), Decimal("0"))
    by_cat = {}
    for x in expenses:
        by_cat[x.category] = by_cat.get(x.category, Decimal("0")) + Decimal(x.amount_aed)
    out = {
        "ym": ym, "label": f"{start:%B %Y}",
        "income": _sum_by_currency(income), "income_aed": aed(income), "payments": len([e for e in income if e.kind == "purchase"]),
        "refunds": _sum_by_currency(refunds), "refunds_aed": aed(refunds),
        "payouts": _sum_by_currency(payouts), "payouts_aed": aed(payouts), "payout_count": len(payouts),
        "expenses_aed": aed(expenses), "expenses_by_cat": by_cat,
        "classes": {s: sum(1 for c in classes if c.status == s) for s in ("completed", "student_missed", "teacher_missed", "cancelled", "scheduled")},
        "missing_aed": sum(1 for r in income + refunds + payouts if r.amount_aed is None),
    }
    out["net_aed"] = out["income_aed"] + out["refunds_aed"] - out["payouts_aed"] - out["expenses_aed"]
    return out


# --- health checks --------------------------------------------------------------------------------
def checks() -> list[dict]:
    """Problems an auditor would ask about. Each: {level, title, items}."""
    found = []

    def add(level, title, items):
        if items:
            found.append({"level": level, "title": title, "items": items[:50], "count": len(items)})

    now = datetime.now(timezone.utc)
    net = dict(db.session.query(CreditEntry.class_id, func.sum(CreditEntry.classes))
               .filter(CreditEntry.class_id.isnot(None)).group_by(CreditEntry.class_id).all())
    earn = {e.class_id: e for e in TeacherEarning.query.all()}
    for_class = ClassSession.query.filter(ClassSession.status != "scheduled").all()
    add("problem", "Classes that took place but did not use a class from the family's balance",
        [f"Class {c.id} on {c.starts_at:%d %b %Y} ({c.status})" for c in for_class
         if c.status in ("completed", "student_missed") and (net.get(c.id) or 0) != -1])
    add("problem", "Classes that did not take place but still used a class from the family's balance",
        [f"Class {c.id} on {c.starts_at:%d %b %Y} ({c.status})" for c in for_class
         if c.status in ("teacher_missed", "cancelled") and (net.get(c.id) or 0) != 0])
    add("problem", "Classes that took place with no teacher pay recorded",
        [f"Class {c.id} on {c.starts_at:%d %b %Y}" for c in for_class
         if c.status in ("completed", "student_missed") and (c.id not in earn or earn[c.id].status == "void")])
    add("problem", "Teacher pay still owed for classes that did not take place",
        [f"Class {c.id} on {c.starts_at:%d %b %Y} ({c.status})" for c in for_class
         if c.status in ("teacher_missed", "cancelled") and c.id in earn and earn[c.id].status in ("owed", "held")])
    add("warning", "Classes not marked by the teacher (more than a day after they started)",
        [f"Class {c.id} on {c.starts_at:%d %b %Y}, teacher {c.teacher.full_name}" for c in
         ClassSession.query.filter(ClassSession.status == "scheduled", ClassSession.starts_at < now - timedelta(days=1)).all()])
    bal = dict(db.session.query(CreditEntry.family_id, func.sum(CreditEntry.classes)).group_by(CreditEntry.family_id).all())
    add("problem", "Families with fewer than zero classes",
        [f"{f.parent_name}: {bal[f.id]} classes" for f in Family.query.all() if (bal.get(f.id) or 0) < 0])
    add("warning", "Payments or refunds without a bank or card reference",
        [f"{e.receipt_no or ('entry ' + str(e.id))}, {e.amount} {e.currency}" for e in
         CreditEntry.query.filter(CreditEntry.kind.in_(("purchase", "refund"))).all() if not e.reference])
    add("problem", "Payments or refunds without a receipt number",
        [f"Entry {e.id}, {e.amount} {e.currency}" for e in
         CreditEntry.query.filter(CreditEntry.kind.in_(("purchase", "refund", "reversal")), CreditEntry.amount.isnot(None)).all() if not e.receipt_no])
    add("warning", "Money records without a dirham (AED) value",
        [f"{e.receipt_no or e.id}: {e.amount} {e.currency}" for e in
         CreditEntry.query.filter(CreditEntry.amount.isnot(None), CreditEntry.amount_aed.is_(None)).all()] +
        [f"{p.voucher_no or p.id}: {p.amount} {p.currency}" for p in Payout.query.filter(Payout.amount_aed.is_(None)).all()])
    bad_payouts = []
    for p in Payout.query.all():
        total = sum((Decimal(e.amount) for e in TeacherEarning.query.filter_by(payout_id=p.id).all()), Decimal("0"))
        if total != Decimal(p.amount):
            bad_payouts.append(f"{p.voucher_no or p.id}: paid {p.amount}, classes add up to {total}")
    add("problem", "Teacher payouts that do not match the classes they cover", bad_payouts)
    add("problem", "Teacher pay marked paid with no payout record",
        [f"Earning {e.id} (class {e.class_id})" for e in TeacherEarning.query.filter(TeacherEarning.status == "paid", TeacherEarning.payout_id.is_(None)).all()])
    held = (ClassSession.query.filter(ClassSession.flagged_at.isnot(None), ClassSession.flag_resolution.is_(None),
                                      ClassSession.flagged_at < now - timedelta(days=7)).all())
    add("warning", "Parent reports waiting more than 7 days for a decision (teacher pay on hold)",
        [f"Class {c.id} on {c.starts_at:%d %b %Y}: {c.flag_reason or ''}"[:160] for c in held])
    zero_rate = [t.full_name for t in Teacher.query.filter_by(active=True).all() if not t.rate]
    add("warning", "Active teachers with no pay per class", zero_rate)
    return found
