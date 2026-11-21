"""Classroom activity: what happened in a class, as times only. Never sound, video or chat.

The classroom page (room.html) watches the person's own microphone, camera, connection and raised hand, and sends
each finished interval here: "microphone off for 42 seconds, ended 3 seconds ago, turned off by the person".
The server works out the clock times itself, so a wrong clock on a family's computer cannot change the record.

Rules (from the academy's classroom policy):
- A microphone off for MORE than 15 seconds is reportable; 15 seconds or less is not shown in reports.
- A camera switched off is always recorded, however short.
- Raising a hand just before muting marks the mute as announced.
- A lost connection, a blocked device or leaving the call is technical, not behaviour.
Nothing here is treated as a disciplinary matter on its own: the report sorts events into "technical",
"announced" and "to review", and a person decides.
"""
from datetime import timedelta

from nurulhuda import db
from nurulhuda.ledger import aware, get_setting, now
from nurulhuda.models import ClassroomEvent, ClassSession

MIC_REPORT_AFTER = 15            # seconds; a mute must last longer than this to be reportable
HAND_BEFORE = 60                 # seconds; a hand raised up to this long before a mute announces it
KINDS = {"mic", "camera", "hand", "network", "join", "leave"}
CAUSES = {"user", "device", "network", "left", "unknown"}
TECHNICAL = {"device", "network", "left"}
LABELS = {"mic": "Microphone off", "camera": "Camera off", "hand": "Raised hand", "network": "Connection lost",
          "join": "Joined", "leave": "Left"}


def window(cs: ClassSession):
    start = aware(cs.starts_at)
    return start - timedelta(minutes=15), start + timedelta(minutes=(cs.minutes or 30) + 30)


def record(cs: ClassSession, role: str, person: str, items: list) -> int:
    """Store finished intervals sent by the classroom page. Returns how many were kept."""
    lo, hi = window(cs)
    t = now()
    kept = 0
    for it in (items or [])[:50]:
        if not isinstance(it, dict):
            continue
        kind = it.get("kind")
        if kind not in KINDS:
            continue
        try:
            ago = max(0.0, min(3600.0, float(it.get("ago") or 0)))           # seconds since it ended
            secs = max(0.0, min(3 * 3600.0, float(it.get("secs") or 0)))     # how long it lasted
        except (TypeError, ValueError):
            continue
        end = t - timedelta(seconds=ago)
        start = end - timedelta(seconds=secs)
        if end < lo or start > hi:
            continue
        cause = it.get("cause") if it.get("cause") in CAUSES else "unknown"
        db.session.add(ClassroomEvent(class_id=cs.id, role=role, person=(person or "")[:120], kind=kind,
                                      started_at=start, ended_at=end if kind not in ("join", "leave") else None,
                                      seconds=int(round(secs)) if kind not in ("join", "leave") else None,
                                      cause=cause, announced=bool(it.get("announced")) and kind == "mic"))
        kept += 1
    return kept


def reportable(e: ClassroomEvent) -> bool:
    if e.kind == "mic":
        return (e.seconds or 0) > MIC_REPORT_AFTER
    return e.kind in ("camera", "network", "hand")


def judge(e: ClassroomEvent, events: list) -> str:
    """technical / announced / review. A mute or camera-off that overlaps a lost connection is technical."""
    if e.kind in ("network",) or e.cause in TECHNICAL:
        return "technical"
    if e.kind == "hand":
        return "announced"
    for n in events:
        if n.kind == "network" and n.role == e.role and n.started_at <= (e.ended_at or e.started_at) \
                and (n.ended_at or n.started_at) >= e.started_at:
            return "technical"
    if e.announced:
        return "announced"
    return "review"


def report(cs: ClassSession) -> dict:
    """Attendance, punctuality and the reportable events of one class, for the teacher's and admin's pages."""
    events = (ClassroomEvent.query.filter_by(class_id=cs.id).order_by(ClassroomEvent.started_at).all())
    start = aware(cs.starts_at)
    people = {}
    for role, joined_at, secs, cam, view in (("teacher", cs.teacher_joined_at, cs.t_secs, cs.t_cam_secs, cs.t_view_secs),
                                             ("student", cs.student_joined_at, cs.s_secs, cs.s_cam_secs, cs.s_view_secs)):
        j = aware(joined_at)
        late = int((j - start).total_seconds() // 60) if j and j > start else 0
        mine = [e for e in events if e.role == role]
        mic = [e for e in mine if e.kind == "mic" and reportable(e)]
        camera = [e for e in mine if e.kind == "camera"]
        people[role] = {
            "name": cs.teacher.full_name if role == "teacher" else cs.student.first_name,
            "joined": j, "late_min": late, "on_time": j is not None and late <= 2,
            "in_call_min": round((secs or 0) / 60), "camera_min": round((cam or 0) / 60), "view_min": round((view or 0) / 60),
            "mic_count": len(mic), "mic_secs": sum(e.seconds or 0 for e in mic),
            "camera_count": len(camera), "camera_secs": sum(e.seconds or 0 for e in camera),
            "network_count": sum(1 for e in mine if e.kind == "network"),
            "hands": sum(1 for e in mine if e.kind == "hand"),
            "short_mutes": sum(1 for e in mine if e.kind == "mic" and not reportable(e)),
        }
    rows = []
    for e in events:
        if not reportable(e):
            continue
        rows.append({"e": e, "label": LABELS[e.kind], "verdict": judge(e, events)})
    to_review = sum(1 for r in rows if r["verdict"] == "review")
    return {"people": people, "rows": rows, "to_review": to_review, "length": cs.minutes or 30,
            "measured": bool(events) or bool(cs.t_secs or cs.s_secs)}


def summary_counts(class_ids: list) -> dict:
    """{class_id: number of events to review}, for lists of classes."""
    if not class_ids:
        return {}
    out = {}
    events = ClassroomEvent.query.filter(ClassroomEvent.class_id.in_(class_ids)).all()
    by_class = {}
    for e in events:
        by_class.setdefault(e.class_id, []).append(e)
    for cid, evs in by_class.items():
        out[cid] = sum(1 for e in evs if reportable(e) and judge(e, evs) == "review")
    return out


# --- classroom background ------------------------------------------------------------------------------
# Daily can blur the room behind a person or replace it with an image, on computer browsers only (not phones).
BACKGROUNDS = {"academy-green": "Academy green", "academy-light": "Academy light", "academy-cream": "Academy cream"}
BG_MODES = {"branded": "Academy background", "blur": "Blurred room", "none": "No effect"}


def background() -> dict:
    """The defaults the admin chose (Admin > Classroom)."""
    mode = get_setting("classroom_bg_mode", "branded")
    mode = mode if mode in BG_MODES else "branded"
    try:
        strength = max(0.1, min(1.0, float(get_setting("classroom_blur_strength", "0.8"))))
    except ValueError:
        strength = 0.8
    custom = get_setting("classroom_bg_url", "").strip()
    name = get_setting("classroom_bg_image", "academy-green")
    if custom.startswith("https://") and custom.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
        image = custom
    else:
        image = f"/static/img/classroom/{name if name in BACKGROUNDS else 'academy-green'}.jpg"
    return {"mode": mode, "strength": strength, "image": image}


def clock(zone: str):
    """'5:33:07 PM' in the viewer's time zone, for the activity report's table."""
    from nurulhuda.timefmt import local

    def hm(dt):
        d = local(dt, zone)
        return d.strftime("%I:%M:%S %p").lstrip("0") if d else ""
    return hm
