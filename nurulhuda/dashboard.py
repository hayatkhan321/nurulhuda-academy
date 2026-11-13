"""The family dashboard: classes left, use this week and month, when classes run out, attendance and each child's
progress. `family_dashboard()` reads the real records; `demo_dashboard()` returns made-up numbers for the public demo.
Both return the same shape, so one template shows either."""
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from nurulhuda import db, ledger, quran_index
from nurulhuda.models import ClassReview, ClassSession, CreditEntry, TeacherCheckin

CHECKIN_AFTER = 6          # classes with a teacher before the family is asked "keep or try another?"
QAIDA_LESSONS = 17         # lessons in the Noorani Qaida (standard edition)
REVIEW_DAYS = 7            # a class can be rated for this many days
DONE = ("completed", "student_missed")      # classes that used a credit


def _local(dt, tz):
    return ledger.aware(dt).astimezone(tz)


def progress_of(cs) -> dict | None:
    """Turn the teacher's 'where we stopped' into words and a percentage."""
    if cs is None:
        return None
    if cs.prog_book == "quran" and cs.prog_surah:
        return quran_progress(cs.prog_surah, cs.prog_verse or 1)
    if cs.prog_book == "qaida" and cs.prog_lesson:
        n = max(1, min(QAIDA_LESSONS, cs.prog_lesson))
        return {"where": f"Noorani Qaida, lesson {n} of {QAIDA_LESSONS}", "pct": round(n / QAIDA_LESSONS * 100),
                "sub": f"{QAIDA_LESSONS - n} lesson{'s' if QAIDA_LESSONS - n != 1 else ''} to finish the Qaida"}
    return None


def presence_of(cs) -> dict | None:
    """Minutes each side was in the class, had the class window in view, and had the camera on."""
    if not (cs.t_secs or cs.s_secs):
        return None
    m = lambda x: round((x or 0) / 60)
    length = cs.minutes or 30
    return {"length": length,
            "teacher": {"in": min(m(cs.t_secs), length + 30), "view": m(cs.t_view_secs), "cam": m(cs.t_cam_secs), "marks": cs.t_marks or 0},
            "student": {"in": min(m(cs.s_secs), length + 30), "view": m(cs.s_view_secs), "cam": m(cs.s_cam_secs)}}


def quran_progress(s: int, v: int) -> dict:
    j, pct = quran_index.juz_progress(s, v)
    return {"where": f"Surah {quran_index.NAMES[s - 1]}, verse {v}", "pct": pct,
            "sub": f"Juz {j}: {pct}% of this juz · {quran_index.quran_percent(s, v)}% of the whole Quran"}


def family_dashboard(family) -> dict:
    tz = ZoneInfo(family.timezone or "UTC")
    today = datetime.now(tz).date()
    kids = [s for s in family.students if s.active] or list(family.students)
    ids = [s.id for s in kids] or [0]
    classes = ClassSession.query.filter(ClassSession.student_id.in_(ids)).order_by(ClassSession.starts_at).all()

    # Classes left, against the "tank" since the last purchase
    balance = ledger.balance(family.id)
    last_buy = (CreditEntry.query.filter_by(family_id=family.id, kind="purchase")
                .order_by(CreditEntry.created_at.desc()).first())
    if last_buy:
        before = sum(e.classes for e in CreditEntry.query.filter(CreditEntry.family_id == family.id,
                                                                  CreditEntry.created_at < last_buy.created_at))
        tank = max(balance, before + last_buy.classes, 1)
        d = _local(last_buy.created_at, tz)
        bought_on = f"{d.day} {d:%b}"
    else:
        tank, bought_on = max(balance, 1), None

    # Usual pace: scheduled classes in the next 4 weeks, or what was taken in the last 4 weeks
    soon = [c for c in classes if c.status == "scheduled" and today <= _local(c.starts_at, tz).date() < today + timedelta(28)]
    recent = [c for c in classes if c.status in DONE and today - timedelta(28) <= _local(c.starts_at, tz).date() <= today]
    per_week = round(len(soon) / 4, 1) if soon else round(len(recent) / 4, 1)
    runout = today + timedelta(days=int(balance / per_week * 7)) if per_week and balance > 0 else None

    def window(start, end):
        inside = [c for c in classes if start <= _local(c.starts_at, tz).date() <= end and c.status != "cancelled"]
        done = sum(1 for c in inside if c.status in DONE)
        return done, len(inside), sum(1 for c in inside if c.status == "teacher_missed")
    week_start = today - timedelta(days=today.weekday())
    w_done, w_plan, _ = window(week_start, week_start + timedelta(days=6))
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    m_done, m_plan, m_teacher_missed = window(month_start, next_month - timedelta(days=1))

    # Attendance over 8 weeks: classes the student came to, out of classes that took place or were missed by them
    weeks = []
    came_total = due_total = 0
    for i in range(7, -1, -1):
        ws = week_start - timedelta(weeks=i)
        inside = [c for c in classes if ws <= _local(c.starts_at, tz).date() <= ws + timedelta(days=6)
                  and c.status in ("completed", "student_missed")]
        came = sum(1 for c in inside if c.status == "completed")
        weeks.append({"label": ws.strftime("%d %b"), "came": came, "due": len(inside)})
        came_total += came; due_total += len(inside)
    peak = max([w["due"] for w in weeks] + [1])
    for w in weeks:
        w["h"] = round(w["came"] / peak * 100) if w["due"] else 0

    # Children
    reviewed = {r.class_id for r in ClassReview.query.filter_by(family_id=family.id)}
    checked = {(c.student_id, c.teacher_id) for c in TeacherCheckin.query.filter(TeacherCheckin.student_id.in_(ids))}
    children, to_review, checkins = [], [], []
    for s in kids:
        mine = [c for c in classes if c.student_id == s.id]
        taken = [c for c in mine if c.status in DONE]
        last = taken[-1] if taken else None
        with_progress = next((c for c in reversed(taken) if progress_of(c)), None)
        teacher = (last or next((c for c in mine if c.status == "scheduled"), None))
        teacher = teacher.teacher if teacher else None
        nxt = next((c for c in mine if c.status == "scheduled" and ledger.aware(c.starts_at) >= ledger.now()), None)
        children.append({
            "name": s.first_name, "age": s.age, "course": s.course or "Course to be set", "teacher": teacher.full_name if teacher else None,
            "progress": progress_of(with_progress), "focus": with_progress.prog_focus if with_progress else None,
            "note": last.teacher_note if last else None, "classes": len(taken),
            "next": _local(nxt.starts_at, tz).strftime("%a %d %b, %I:%M %p").replace(" 0", " ") if nxt else None,
        })
        if teacher:
            with_teacher = [c for c in taken if c.teacher_id == teacher.id and c.status == "completed"]
            if len(with_teacher) >= CHECKIN_AFTER and (s.id, teacher.id) not in checked:
                checkins.append({"student_id": s.id, "teacher_id": teacher.id, "student": s.first_name,
                                 "teacher": teacher.full_name, "count": len(with_teacher)})
        for c in taken:
            if c.status == "completed" and c.id not in reviewed and ledger.aware(c.starts_at) >= ledger.now() - timedelta(days=REVIEW_DAYS):
                to_review.append({"id": c.id, "student": s.first_name, "teacher": c.teacher.full_name,
                                  "when": _local(c.starts_at, tz).strftime("%a %d %b")})
    # Teacher presence over the last 4 weeks: minutes in class out of class minutes, for classes the system measured
    measured = [c for c in classes if c.status == "completed" and c.t_secs and
                today - timedelta(28) <= _local(c.starts_at, tz).date() <= today]
    due_secs = sum((c.minutes or 30) * 60 for c in measured)
    presence = None
    if due_secs:
        presence = {"classes": len(measured),
                    "teacher": min(100, round(sum(c.t_secs for c in measured) / due_secs * 100)),
                    "view": min(100, round(sum(c.t_view_secs for c in measured) / due_secs * 100)),
                    "student": min(100, round(sum(c.s_secs for c in measured) / due_secs * 100))}
    nxt_all = next((c for c in classes if c.status == "scheduled" and ledger.aware(c.starts_at) >= ledger.now()), None)
    return {
        "demo": False, "balance": balance, "tank": tank, "bought_on": bought_on,
        "pct_left": round(max(0, balance) / tank * 100) if tank else 0,
        "per_week": per_week, "runout": f"{runout.day} {runout:%B}" if runout else None,
        "week": {"done": w_done, "plan": w_plan}, "month": {"done": m_done, "plan": m_plan, "teacher_missed": m_teacher_missed},
        "next": f"{_local(nxt_all.starts_at, tz).strftime('%a %I:%M %p').replace(' 0', ' ')}, {nxt_all.student.first_name}" if nxt_all else None,
        "weeks": weeks, "attendance": round(came_total / due_total * 100) if due_total else None,
        "children": children, "to_review": to_review[-6:], "checkins": checkins, "presence": presence,
        "last_class": next(({"when": f"{_local(c.starts_at, tz).strftime('%a %d %b')}, {c.student.first_name} with {c.teacher.full_name}",
                             "p": presence_of(c)} for c in reversed(classes) if c.status in DONE and presence_of(c)), None),
    }


def demo_dashboard() -> dict:
    """Example numbers for the public demo: a family with two children."""
    today = date.today()
    weeks = []
    for i, (came, due) in enumerate([(4, 5), (5, 5), (3, 5), (5, 5), (5, 5), (4, 5), (5, 5), (3, 3)]):
        ws = today - timedelta(days=today.weekday(), weeks=7 - i)
        weeks.append({"label": ws.strftime("%d %b"), "came": came, "due": due, "h": round(came / 5 * 100)})
    return {
        "demo": True, "balance": 14, "tank": 24, "bought_on": f"{(today - timedelta(days=10)).day} {(today - timedelta(days=10)):%b}",
        "pct_left": 58, "per_week": 5, "runout": f"{(today + timedelta(days=19)).day} {(today + timedelta(days=19)):%B}",
        "week": {"done": 3, "plan": 5}, "month": {"done": 10, "plan": 20, "teacher_missed": 1},
        "next": "Thu 5:00 PM, Yusuf", "weeks": weeks, "attendance": 92,
        "children": [
            {"name": "Yusuf", "age": "10", "course": "Tajweed", "teacher": "Ustadh Bilal", "classes": 18,
             "progress": quran_progress(67, 26),
             "focus": "Ikhfa and madd", "note": "Clear reading today. Practise verses 10 to 12 twice a day.", "next": "Thu 13 Nov, 5:00 PM"},
            {"name": "Maryam", "age": "6", "course": "Noorani Qaida", "teacher": "Ustadha Sana", "classes": 6,
             "progress": {"where": "Noorani Qaida, lesson 8 of 17", "pct": 47, "sub": "9 lessons to finish the Qaida"},
             "focus": "Letters with fatha", "note": "Lovely effort. Revise lesson 7 before Saturday.", "next": "Sat 15 Nov, 10:00 AM"},
        ],
        "to_review": [{"id": 0, "student": "Yusuf", "teacher": "Ustadh Bilal", "when": "Tue"}],
        "presence": {"classes": 18, "teacher": 98, "view": 95, "student": 96},
        "last_class": {"when": "Tue, Yusuf with Ustadh Bilal", "p": {"length": 30,
                       "teacher": {"in": 30, "view": 29, "cam": 30, "marks": 14}, "student": {"in": 29, "view": 27, "cam": 29}}},
        "checkins": [{"student_id": 0, "teacher_id": 0, "student": "Maryam", "teacher": "Ustadha Sana", "count": 6}],
    }
