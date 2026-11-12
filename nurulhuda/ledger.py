"""The academy's money rules, in one place.

- A family's balance is the sum of their credit entries.
- A class that took place, or that the student missed, uses one class and earns the teacher their rate
  (the rate is per 30 minutes, so a 60-minute class earns twice the rate).
- A class the teacher missed, or that was cancelled, uses nothing and earns nothing.
- If a family reports a problem, the teacher's pay for that class is held until a supervisor decides.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from nurulhuda import db
from nurulhuda.models import ClassSession, CreditEntry, Setting, Teacher, TeacherEarning

USES_CREDIT = {"completed", "student_missed"}
FLAG_WINDOW = timedelta(hours=48)

STATUS_LABELS = {
    "scheduled": "Scheduled", "completed": "Completed", "student_missed": "Student absent",
    "teacher_missed": "Teacher absent", "cancelled": "Cancelled",
}


def now():
    return datetime.now(timezone.utc)


def aware(dt):
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def balance(family_id: int) -> int:
    return int(db.session.query(func.coalesce(func.sum(CreditEntry.classes), 0))
               .filter(CreditEntry.family_id == family_id).scalar() or 0)


def get_setting(key: str, default: str) -> str:
    row = db.session.get(Setting, key)
    return row.value if row else default


def set_setting(key: str, value: str) -> None:
    row = db.session.get(Setting, key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))


def teacher_limit() -> int:
    try:
        return int(get_setting("teacher_limit", "5"))
    except ValueError:
        return 5


def active_teacher_count() -> int:
    return Teacher.query.filter_by(active=True).count()


def set_status(cs: ClassSession, status: str, note: str | None = None) -> None:
    """Change a class's status and keep credits and teacher pay consistent. Safe to call twice."""
    family_id = cs.student.family_id
    used = CreditEntry.query.filter_by(class_id=cs.id, kind="used").first()
    earning = TeacherEarning.query.filter_by(class_id=cs.id).first()
    cs.status = status
    if note is not None:
        cs.teacher_note = note
    if status in USES_CREDIT:
        if not used:
            db.session.add(CreditEntry(family_id=family_id, classes=-1, kind="used", class_id=cs.id,
                                       note=f"Class on {cs.starts_at:%d %b %Y}"))
        if not earning:
            db.session.add(TeacherEarning(teacher_id=cs.teacher_id, class_id=cs.id, amount=class_pay(cs),
                                          currency=cs.teacher.rate_currency,
                                          status="held" if cs.flagged_at and not cs.flag_resolution else "owed"))
        elif earning.status == "void":
            earning.status = "owed"
    else:
        if used:
            returned = CreditEntry.query.filter_by(class_id=cs.id, kind="returned").first()
            if not returned:
                db.session.add(CreditEntry(family_id=family_id, classes=1, kind="returned", class_id=cs.id,
                                           note="Class not charged"))
        if earning and earning.status in ("owed", "held"):
            earning.status = "void"


def class_pay(cs: ClassSession):
    """A teacher's rate is per 30 minutes, so a 60-minute hifz class pays double."""
    from decimal import Decimal
    rate = Decimal(cs.teacher.rate or 0)
    return (rate * Decimal(cs.minutes or 30) / 30).quantize(Decimal("0.01"))


def flag(cs: ClassSession, reason: str) -> None:
    cs.flagged_at = now()
    cs.flag_reason = reason
    cs.flag_resolution = None
    earning = TeacherEarning.query.filter_by(class_id=cs.id).first()
    if earning and earning.status == "owed":
        earning.status = "held"


def can_flag(cs: ClassSession) -> bool:
    end = aware(cs.starts_at) + timedelta(minutes=cs.minutes)
    return cs.status != "scheduled" and not cs.flagged_at and now() <= end + FLAG_WINDOW


def resolve(cs: ClassSession, decision: str, note: str) -> None:
    """decision: 'pay' keeps the class as it was and releases the teacher's pay; 'refund' returns the class
    to the family and cancels the teacher's pay."""
    cs.flag_resolution = f"{decision}: {note}"[:200]
    earning = TeacherEarning.query.filter_by(class_id=cs.id).first()
    if decision == "pay":
        if earning and earning.status == "held":
            earning.status = "owed"
    else:
        set_status(cs, "teacher_missed")
