"""Standard, Gold and Diamond memberships, and which teachers may teach which families.

Nothing about prices is fixed in code: multipliers, longest class, benefits, the offer of the month and the bar a
teacher must clear for each level are all settings, changed in Admin > Memberships.

- A Gold family pays the Standard price times the Gold multiplier (2 to start); Diamond times 3.
- Gold and Diamond families may book 60-minute classes (the price follows the minutes).
- Gold and Diamond families are taught only by teachers the academy has placed at that level, and a teacher can
  only be placed there after clearing the bar: verified qualifications, years of experience, classes taught,
  reliability, parents' ratings (with enough of them), and no upheld conduct concern in the last year.
- Language: a family that asked for English (or Urdu, or Arabic) is only matched with teachers who speak it at the
  level the academy requires (Fluent by default), ideally checked by an admin.
"""
from datetime import timedelta
from decimal import Decimal

from nurulhuda import content as C
from nurulhuda import db
from nurulhuda.ledger import get_setting, now
from nurulhuda.models import ClassReview, ClassSession, ConductReport

TIERS = ("standard", "gold", "diamond")
RANK = {t: i for i, t in enumerate(TIERS)}
DEFAULTS = {
    "standard": {"label": "Standard", "multiplier": "1", "max_minutes": "30", "offer_pct": "0", "offer_label": "",
                 "benefits": "Tested, qualified teachers\nOne-to-one live classes\nA report after every class",
                 "min_rating": "0", "min_reviews": "0", "min_classes": "0", "min_years": "0", "max_missed_pct": "100",
                 "need_verified": "0"},
    "gold": {"label": "Gold", "multiplier": "2", "max_minutes": "60", "offer_pct": "0", "offer_label": "",
             "benefits": "Higher-rated, selected teachers\nPriority choice of teacher\nMore flexible times and more choice of times\n"
                         "Classes of 30 or 60 minutes",
             "min_rating": "4.6", "min_reviews": "5", "min_classes": "40", "min_years": "2", "max_missed_pct": "5",
             "need_verified": "1"},
    "diamond": {"label": "Diamond", "multiplier": "3", "max_minutes": "60", "offer_pct": "0", "offer_label": "",
                "benefits": "Our highest-rated, most experienced teachers\nFirst choice of teacher\nThe most flexible times\n"
                            "Classes of 30 or 60 minutes\nPriority booking and support",
                "min_rating": "4.8", "min_reviews": "10", "min_classes": "100", "min_years": "5", "max_missed_pct": "2",
                "need_verified": "1"},
}
FIELDS = tuple(DEFAULTS["gold"].keys())


def setting(tier: str, field: str) -> str:
    return get_setting(f"tier_{tier}_{field}", DEFAULTS[tier][field])


def _dec(tier, field, lo, hi):
    try:
        return max(Decimal(lo), min(Decimal(hi), Decimal(setting(tier, field))))
    except Exception:
        return Decimal(DEFAULTS[tier][field])


def on() -> bool:
    """Are Gold and Diamond offered to families yet? Off until the academy has teachers placed at those levels."""
    return get_setting("memberships_on", "0") == "1"


def config(tier: str) -> dict:
    tier = tier if tier in TIERS else "standard"
    return {
        "key": tier, "label": setting(tier, "label") or DEFAULTS[tier]["label"],
        "multiplier": _dec(tier, "multiplier", "1", "10") if tier != "standard" else Decimal("1"),
        "max_minutes": 60 if setting(tier, "max_minutes") == "60" else 30,
        "offer_pct": _dec(tier, "offer_pct", "0", "50"), "offer_label": setting(tier, "offer_label"),
        "benefits": [b.strip() for b in setting(tier, "benefits").splitlines() if b.strip()],
        "min_rating": _dec(tier, "min_rating", "0", "5"), "min_reviews": int(_dec(tier, "min_reviews", "0", "1000")),
        "min_classes": int(_dec(tier, "min_classes", "0", "100000")), "min_years": int(_dec(tier, "min_years", "0", "60")),
        "max_missed_pct": _dec(tier, "max_missed_pct", "0", "100"), "need_verified": setting(tier, "need_verified") == "1",
    }


def offered() -> list:
    """Memberships a family can choose now."""
    return [config(t) for t in (TIERS if on() else ("standard",))]


def minutes_allowed(tier: str) -> tuple:
    return (30, 60) if config(tier)["max_minutes"] >= 60 else (30,)


# --- teachers ------------------------------------------------------------------------------------------
def teacher_stats(teacher) -> dict:
    classes = ClassSession.query.filter(ClassSession.teacher_id == teacher.id, ClassSession.starts_at <= now()).all()
    done = sum(1 for c in classes if c.status == "completed")
    missed = sum(1 for c in classes if c.status == "teacher_missed")
    reviews = ClassReview.query.filter_by(teacher_id=teacher.id).all()
    upheld = ConductReport.query.filter(ConductReport.teacher_id == teacher.id, ConductReport.status == "upheld",
                                        ConductReport.created_at >= now() - timedelta(days=365)).count()
    return {"done": done, "missed_pct": round(missed / (done + missed) * 100, 1) if done + missed else 0,
            "rating": round(sum(r.stars for r in reviews) / len(reviews), 2) if reviews else None,
            "reviews": len(reviews), "years": teacher.experience_years or 0, "upheld": upheld,
            "verified": bool(teacher.qualifications_verified)}


def eligibility(teacher, stats: dict | None = None) -> dict:
    """{tier: {"ok": bool, "checks": [(label, passed)]}} for Gold and Diamond."""
    s = stats or teacher_stats(teacher)
    out = {"standard": {"ok": True, "checks": []}}
    for tier in ("gold", "diamond"):
        c = config(tier)
        checks = []
        if c["need_verified"]:
            checks.append(("Qualifications checked by the academy", s["verified"]))
        checks.append((f"At least {c['min_years']} years' teaching experience", s["years"] >= c["min_years"]))
        checks.append((f"At least {c['min_classes']} classes taught here", s["done"] >= c["min_classes"]))
        checks.append((f"Missed no more than {c['max_missed_pct']}% of classes", Decimal(str(s["missed_pct"])) <= c["max_missed_pct"]))
        checks.append((f"Parents' rating {c['min_rating']} or more, from at least {c['min_reviews']} reviews",
                       s["rating"] is not None and s["reviews"] >= c["min_reviews"] and Decimal(str(s["rating"])) >= c["min_rating"]))
        checks.append(("No upheld conduct concern in the last year", s["upheld"] == 0))
        out[tier] = {"ok": all(ok for _, ok in checks), "checks": checks}
    return out


# --- matching ------------------------------------------------------------------------------------------
LANG_FIELDS = {"English": ("english_level", "english_verified"), "Urdu": ("urdu_level", "urdu_verified"),
               "Arabic": ("arabic_level", "arabic_verified")}


def min_level() -> str:
    lvl = get_setting("match_min_level", "Fluent")
    return lvl if lvl in C.LEVELS else "Fluent"


def need_verified_language() -> bool:
    return get_setting("match_need_verified", "0") == "1"


def language_ok(teacher, family) -> tuple[bool, str | None]:
    """Can this teacher teach in the language the family asked for?"""
    lang = (family.instruction_language or "").strip() if family else ""
    if lang not in LANG_FIELDS:
        return True, None
    level_field, verified_field = LANG_FIELDS[lang]
    level = getattr(teacher, level_field) or "None"
    need = min_level()
    good = level in C.LEVELS and C.LEVELS.index(level) <= C.LEVELS.index(need)
    if not good:
        return False, f"{teacher.full_name}'s {lang} is recorded as {level}; this family needs {need} or better."
    if need_verified_language() and not getattr(teacher, verified_field):
        return False, f"{teacher.full_name}'s {lang} has not been checked by an admin yet."
    return True, None


def tier_ok(teacher, family) -> tuple[bool, str | None]:
    want = family.membership if family and family.membership in TIERS else "standard"
    have = teacher.tier if teacher.tier in TIERS else "standard"
    if RANK[have] >= RANK[want]:
        return True, None
    return False, f"This is a {config(want)['label']} family; {teacher.full_name} is not placed at that level."


def suitable(teacher, family) -> tuple[bool, list]:
    problems = [msg for ok, msg in (language_ok(teacher, family), tier_ok(teacher, family)) if not ok]
    return not problems, problems
