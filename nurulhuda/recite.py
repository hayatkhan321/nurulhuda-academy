"""Practice check (staff test): a teacher or the Head of Academics records a verse, the HisnLabs tajweed-v2 model
(Apache-2.0) hears it in the browser, and the rule engine here (nurulhuda/vendor/hisnlabs/imam.py, Apache-2.0) turns
what it heard into remarks per word. Staff then mark each remark right or wrong, so we learn how far the check can be
trusted for children and adults, boys and girls, before any family ever sees it.

Privacy: the recording never leaves the browser. The server gets only the model's phonetic script, its confidence
and timings, and the labels chosen on the page (child/adult, male/female). No names.

The model was trained mostly on adult men: for children the check is gentler (it only remarks when it is very sure).
It never replaces the teacher: every remark is a suggestion for the teacher to confirm.
"""
import json
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from nurulhuda import auth, db, quran_index
from nurulhuda.models import PracticeCheck

recite_bp = Blueprint("recite", __name__, url_prefix="/staff/practice-check")

READERS = {"child": "Child", "adult": "Adult"}
GENDERS = {"male": "Male", "female": "Female"}
# How sure the model must be before it says anything (see imam.listen): fine points / clear mistakes.
STRICTNESS = {"standard": (0.3, 0.7), "gentle": (0.6, 0.85)}
# Remarks the check gets right. Measured 17 Nov 2026 on the qdat_bench benchmark (159 reciters of 5:109, Apache-2.0):
# qalqalah 48/48, ghunnah 30/31, ikhfa 17/17 right. Iqlab and idgham (same nasal family) are not in that verse.
# Wrong letter, dropped or added sound, vowel, shadda and madd-length remarks were mostly wrong (2-18 %): the model
# misheard rather than the reciter erred. Those are still shown, apart and greyed, as "less sure".
SURE_RULES = {"qalqalah", "ghunnah", "ikhfa", "iqlab", "idgham"}
MAX_SECONDS = 28


def _staff():
    """(teacher or None, is_admin) for a signed-in teacher or admin; None if neither."""
    if auth.is_admin():
        return None, True
    t = auth.current_teacher()
    return (t, False) if t else None


def _engine():
    from nurulhuda.vendor.hisnlabs import imam  # heavy-ish import: only when a check runs
    from quran_transcript import Aya
    return imam, Aya


def analyse(surah, ayah, heard, probs, times, strictness="standard"):
    """Per-word remarks for one verse. Returns a list of {i, word, ok, notes:[{en, ar, rule, severity}], madd:[..]}."""
    imam, Aya = _engine()
    words = Aya(surah, ayah).get().uthmani.split(" ")
    lo, jali = STRICTNESS.get(strictness, STRICTNESS["standard"])
    ref = imam.recited(words, heard)
    out = []
    for w in imam.listen(ref, heard, heard_probs=probs or None, min_prob=lo, min_prob_jali=jali,
                         langs=("en", "ar"), heard_times=times or None):
        notes = [{"en": n["msg"]["en"], "ar": n["msg"]["ar"], "rule": n.get("rule"), "severity": n.get("severity"),
                  "sure": (n.get("rule") or "").split(":")[0] in SURE_RULES} for n in w["notes"]]
        out.append({
            "i": w.get("index"),
            "ok": bool(w["ok"]),
            "sure": any(n["sure"] for n in notes),
            "notes": notes,
            "madd": [{"en": m["name"]["en"], "ar": m["name"]["ar"], "heard": m["heard"]} for m in w.get("madd", [])],
        })
    # Reading only part of a long verse is normal: words before the first and after the last word recited are
    # "not recited", not mistakes.
    def unread(w):
        return w["notes"] and all((n["rule"] or "") in ("word", "dropped") for n in w["notes"])
    lo_i, hi_i = 0, len(out)
    while lo_i < hi_i and unread(out[lo_i]):
        lo_i += 1
    while hi_i > lo_i and unread(out[hi_i - 1]):
        hi_i -= 1
    for k, w in enumerate(out):
        if k < lo_i or k >= hi_i:
            w.update(ok=True, sure=False, notes=[], madd=[], skipped=True)
    return {"words": len(words), "result": out, "recited": hi_i - lo_i}


@recite_bp.route("/")
def page():
    who = _staff()
    if not who:
        return redirect(url_for("portal.login"))
    return render_template("practice_check.html", title="Practice check (staff test)", READERS=READERS, GENDERS=GENDERS,
                           SURAHS=quran_index.NAMES, VERSES=quran_index.VERSES, MAX_SECONDS=MAX_SECONDS,
                           is_admin=who[1])


def _json_guard():
    who = _staff()
    if not who:
        abort(403)
    if request.headers.get("X-CSRF") != session.get("csrf"):
        abort(400)
    return who


@recite_bp.route("/check", methods=["POST"])
def check():
    teacher, _ = _json_guard()
    d = request.get_json(silent=True) or {}
    try:
        surah, ayah = int(d.get("surah")), int(d.get("ayah"))
    except (TypeError, ValueError):
        abort(400)
    if not (1 <= surah <= 114 and 1 <= ayah <= quran_index.VERSES[surah - 1]):
        abort(400)
    reader = d.get("reader") if d.get("reader") in READERS else abort(400)
    gender = d.get("gender") if d.get("gender") in GENDERS else abort(400)
    heard = str(d.get("heard") or "")[:4000]
    probs = [float(p) for p in (d.get("probs") or [])][:4000]
    times = [float(t) for t in (d.get("times") or [])][:4001]
    if not heard or len(probs) != len(heard) or len(times) != len(heard) + 1:
        return jsonify(error="The model heard nothing. Record again, a little closer to the microphone."), 422
    strictness = "gentle" if reader == "child" else "standard"
    try:
        res = analyse(surah, ayah, heard, probs, times, strictness)
    except Exception:  # noqa: BLE001 - a recitation of another verse can confuse the aligner
        res = None
    if not res or not res["recited"]:
        return jsonify(error="The check could not match this recording to the verse. Was it the verse chosen above?"), 422
    row = PracticeCheck(teacher_id=teacher.id if teacher else None, reader=reader, gender=gender, strictness=strictness,
                        surah=surah, ayah=ayah, seconds=min(float(d.get("seconds") or 0), 60), heard=heard,
                        result=json.dumps(res["result"], ensure_ascii=False),
                        flagged=sum(1 for w in res["result"] if w.get("sure")))
    db.session.add(row)
    db.session.commit()
    return jsonify(id=row.id, strictness=strictness, words=res["words"], result=res["result"])


@recite_bp.route("/<int:pid>/review", methods=["POST"])
def review(pid):
    teacher, admin = _json_guard()
    row = db.session.get(PracticeCheck, pid) or abort(404)
    if not admin and row.teacher_id != teacher.id:
        abort(403)
    d = request.get_json(silent=True) or {}
    marks = {str(int(k)): v for k, v in (d.get("marks") or {}).items() if v in ("right", "wrong", "missed")}
    row.review = json.dumps(marks)
    row.review_note = str(d.get("note") or "")[:500] or None
    row.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(ok=True)


def summary():
    """Per reader group: checks, reviewed, remarks the staff said were right / wrong, mistakes the check missed."""
    groups = {}
    for r in PracticeCheck.query.order_by(PracticeCheck.created_at.desc()).limit(2000):
        g = groups.setdefault((r.reader, r.gender), {"checks": 0, "reviewed": 0, "right": 0, "wrong": 0, "missed": 0})
        g["checks"] += 1
        if r.review is None:
            continue
        g["reviewed"] += 1
        marks = json.loads(r.review or "{}")
        for v in marks.values():
            g[v] += 1
    rows = []
    for (reader, gender), g in sorted(groups.items()):
        said = g["right"] + g["wrong"]
        rows.append({"reader": READERS[reader], "gender": GENDERS[gender], **g,
                     "precision": round(100 * g["right"] / said) if said else None})
    return rows


@recite_bp.route("/results")
def results():
    who = _staff()
    if not who:
        return redirect(url_for("portal.login"))
    q = PracticeCheck.query.order_by(PracticeCheck.created_at.desc())
    if not who[1]:
        q = q.filter_by(teacher_id=who[0].id)
    recent = []
    for r in q.limit(60):
        recent.append({"r": r, "surah": quran_index.NAMES[r.surah - 1], "marks": json.loads(r.review or "{}"),
                       "result": json.loads(r.result or "[]")})
    return render_template("practice_check_results.html", title="Practice check results", rows=summary() if who[1] else [],
                           recent=recent, READERS=READERS, GENDERS=GENDERS, is_admin=who[1])
