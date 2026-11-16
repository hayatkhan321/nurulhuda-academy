"""Practice between classes: the homework card and the mistakes the teacher marks on the lesson board.

Homework is set by the teacher when marking a class; the family ticks each day they practised. Mistakes are words
the teacher taps on the Quran page during class; each stays open (shown to the family as "words to practise") until
the teacher marks it corrected in a later class.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from nurulhuda import db, quran_index
from nurulhuda.ledger import aware, now
from nurulhuda.models import Homework, Mistake

KINDS = {"word": "Word", "tajweed": "Tajweed", "harakah": "Vowel marks"}
MINUTES = (5, 10, 15, 20, 30)
SHOW_HOMEWORK_DAYS = 21      # an old homework card disappears after three weeks
MAX_DAYS_KEPT = 60


# --- homework ----------------------------------------------------------------------------------------------------
def save_homework(cs, form) -> Homework | None:
    """Create or replace the homework set in this class, from the teacher's marking form."""
    task = " ".join((form.get("hw_task") or "").split())[:300]
    hw = Homework.query.filter_by(class_id=cs.id).first()
    if not task:
        if hw:
            db.session.delete(hw)
        return None
    hw = hw or Homework(class_id=cs.id, student_id=cs.student_id, teacher_id=cs.teacher_id)
    hw.task = task
    mins = form.get("hw_minutes", type=int)
    hw.minutes = mins if mins in MINUTES else None
    hw.book = hw.surah = hw.verse_from = hw.verse_to = hw.lesson = None
    surah = form.get("hw_surah", type=int)
    lesson = form.get("hw_lesson", type=int)
    if surah and 1 <= surah <= 114:
        top = quran_index.VERSES[surah - 1]
        a = max(1, min(top, form.get("hw_from", type=int) or 1))
        b = max(a, min(top, form.get("hw_to", type=int) or a))
        hw.book, hw.surah, hw.verse_from, hw.verse_to = "quran", surah, a, b
    elif lesson and 1 <= lesson <= 40:
        hw.book, hw.lesson = "qaida", lesson
    db.session.add(hw)
    return hw


def portion(hw) -> str | None:
    if hw.book == "quran" and hw.surah:
        name = quran_index.NAMES[hw.surah - 1]
        if hw.verse_from == hw.verse_to:
            return f"Surah {name}, verse {hw.verse_from}"
        return f"Surah {name}, verses {hw.verse_from} to {hw.verse_to}"
    if hw.book == "qaida" and hw.lesson:
        return f"Noorani Qaida, lesson {hw.lesson}"
    return None


def current_homework(student_id) -> Homework | None:
    hw = Homework.query.filter_by(student_id=student_id).order_by(Homework.created_at.desc()).first()
    if hw and aware(hw.created_at) >= now() - timedelta(days=SHOW_HOMEWORK_DAYS):
        return hw
    return None


def _days(hw) -> list[str]:
    return [d for d in (hw.days or "").split(",") if d]


def local_today(tzname) -> date:
    return datetime.now(ZoneInfo(tzname or "UTC")).date()


def mark_practised(hw, tzname) -> bool:
    """Tick today for this homework; returns False if today was already ticked."""
    today = local_today(tzname).isoformat()
    days = _days(hw)
    if today in days:
        return False
    hw.days = ",".join((days + [today])[-MAX_DAYS_KEPT:])
    return True


def homework_view(hw, tzname) -> dict:
    """What the family dashboard shows for one homework card."""
    tz = ZoneInfo(tzname or "UTC")
    today = local_today(tzname)
    set_on = aware(hw.created_at).astimezone(tz).date()
    days = {date.fromisoformat(d) for d in _days(hw)}
    since = sorted(d for d in days if d >= set_on)
    # the last 7 days, oldest first, for the row of dots
    week = [{"label": (today - timedelta(days=i)).strftime("%a"), "done": (today - timedelta(days=i)) in days,
             "today": i == 0} for i in range(6, -1, -1)]
    streak, d = 0, today if today in days else today - timedelta(days=1)
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return {"id": hw.id, "task": hw.task, "portion": portion(hw), "minutes": hw.minutes,
            "teacher": hw.teacher.full_name if hw.teacher else None, "set_on": f"{set_on.day} {set_on:%b}",
            "days_since": len(since), "days_open": (today - set_on).days + 1, "today_done": today in days,
            "week": week, "streak": streak}


# --- mistakes ----------------------------------------------------------------------------------------------------
def valid_word(surah, ayah, word) -> bool:
    return (isinstance(surah, int) and 1 <= surah <= 114 and isinstance(ayah, int)
            and 1 <= ayah <= quran_index.VERSES[surah - 1] and isinstance(word, int) and 1 <= word <= 140)


def board_mistakes(cs) -> list[dict]:
    """For the lesson board: this child's open mistakes, and those marked or corrected in this class."""
    rows = Mistake.query.filter(Mistake.student_id == cs.student_id,
                                db.or_(Mistake.fixed_at.is_(None), Mistake.fixed_class_id == cs.id)).all()
    out = []
    for m in rows:
        if m.fixed_at is not None:
            state = "fixed"
        elif m.last_class_id == cs.id:
            state = "now"
        else:
            state = "open"
        out.append({"s": m.surah, "a": m.ayah, "w": m.word, "kind": m.kind, "state": state})
    return out


def apply_mistake(cs, data) -> dict:
    """One tap by the teacher on the board. Actions: add (this class), remove (undo this class's mark),
    fix (an earlier mistake read correctly now), unfix (undo a fix made in this class)."""
    action = data.get("action")
    s, a, w = data.get("s"), data.get("a"), data.get("w")
    if not valid_word(s, a, w):
        return {"ok": False, "error": "bad word"}
    m = Mistake.query.filter_by(student_id=cs.student_id, surah=s, ayah=a, word=w).filter(
        db.or_(Mistake.fixed_at.is_(None), Mistake.fixed_class_id == cs.id)).order_by(Mistake.id.desc()).first()
    if action == "add":
        kind = data.get("kind") if data.get("kind") in KINDS else "word"
        text = " ".join(str(data.get("text") or "").split())[:80] or "?"
        if m and m.fixed_at is None:
            if m.last_class_id != cs.id:
                m.times += 1
            m.last_class_id, m.kind = cs.id, kind
        else:
            m = Mistake(student_id=cs.student_id, teacher_id=cs.teacher_id, class_id=cs.id, last_class_id=cs.id,
                        surah=s, ayah=a, word=w, text=text, kind=kind)
            db.session.add(m)
        return {"ok": True, "state": "now"}
    if not m:
        return {"ok": True, "state": None}
    if action == "remove" and m.fixed_at is None and m.last_class_id == cs.id:
        if m.class_id == cs.id and m.times <= 1:
            db.session.delete(m)
            return {"ok": True, "state": None}
        m.times = max(1, m.times - 1)
        return {"ok": True, "state": "open"}
    if action == "fix" and m.fixed_at is None:
        m.fixed_at, m.fixed_class_id = now(), cs.id
        return {"ok": True, "state": "fixed"}
    if action == "unfix" and m.fixed_class_id == cs.id:
        m.fixed_at = m.fixed_class_id = None
        return {"ok": True, "state": "open"}
    return {"ok": True, "state": None}


def class_counts(cs) -> dict:
    """For the teacher's marking form: mistakes marked and corrected in this class, and still open for the child."""
    marked = Mistake.query.filter(Mistake.last_class_id == cs.id, Mistake.fixed_at.is_(None)).count()
    fixed = Mistake.query.filter_by(fixed_class_id=cs.id).count()
    open_ = Mistake.query.filter(Mistake.student_id == cs.student_id, Mistake.fixed_at.is_(None)).count()
    return {"marked": marked, "fixed": fixed, "open": open_}


def words_to_practise(student_id, limit=12) -> dict:
    """For the family dashboard: open mistakes, newest first, and how many have been corrected."""
    rows = (Mistake.query.filter(Mistake.student_id == student_id, Mistake.fixed_at.is_(None))
            .order_by(Mistake.last_class_id.desc(), Mistake.surah, Mistake.ayah, Mistake.word).all())
    fixed = Mistake.query.filter(Mistake.student_id == student_id, Mistake.fixed_at.isnot(None)).count()
    items = [{"text": m.text, "kind": KINDS.get(m.kind, "Word"), "where": f"{quran_index.NAMES[m.surah - 1]} {m.surah}:{m.ayah}",
              "times": m.times} for m in rows[:limit]]
    return {"items": items, "open": len(rows), "more": max(0, len(rows) - limit), "fixed": fixed}
