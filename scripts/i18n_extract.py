"""List every English line visitors see, so it can be translated.

    python scripts/i18n_extract.py            # writes nurulhuda/i18n/_strings.json and reports what each language is missing
"""
import json
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "x.db")
os.environ.pop("DB_PASSWORD", None)
os.environ["ADMIN_PASSWORD"] = ""

from nurulhuda import create_app, db, i18n  # noqa: E402
from nurulhuda.ledger import now  # noqa: E402
from nurulhuda.models import ClassSession, CreditEntry, Family, Student, Teacher  # noqa: E402

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False
seen: dict[str, None] = {}


def grab(client, path, method="get", **kw):
    r = getattr(client, method)(path, **kw)
    if r.status_code in (200, 400) and r.mimetype == "text/html":
        for s in i18n.collect_strings(r.get_data(as_text=True)):
            seen.setdefault(s, None)


with app.app_context():
    fam = Family(parent_name="Amina", email="a@example.com", timezone="America/Toronto")
    db.session.add(fam); db.session.flush()
    st = Student(family_id=fam.id, first_name="Yusuf", course="Nazira")
    te = Teacher(full_name="Fatima", email="f@example.com", active=True, rate=5)
    db.session.add_all([st, te]); db.session.flush()
    db.session.add(CreditEntry(family_id=fam.id, classes=10, kind="purchase"))
    for i, status in enumerate(["completed", "scheduled", "student_missed", "teacher_missed", "cancelled"]):
        db.session.add(ClassSession(student_id=st.id, teacher_id=te.id, starts_at=now() + timedelta(days=i - 2, minutes=5),
                                    status=status, teacher_note="Good" if status == "completed" else None))
    db.session.commit()
    fid, tid, cid = fam.id, te.id, ClassSession.query.filter_by(status="scheduled").first().id

pages = ["/", "/courses", "/families", "/free-trial", "/teach", "/about", "/vision", "/discover-islam", "/videos",
         "/contact", "/terms", "/app", "/offline", "/thanks/trial", "/thanks/teacher", "/thanks/islam", "/login",
         "/no-such-page"]
c = app.test_client()
for p in pages:
    grab(c, p)
with c.session_transaction() as s:
    csrf = s.get("csrf")
for p in ["/free-trial", "/teach", "/discover-islam", "/login"]:
    grab(c, p, "post", data={"csrf": csrf})
    grab(c, p, "post", data={"csrf": csrf, "email": "bad"})
for role, uid, pages in (("family", fid, ["/my", f"/class/{cid}"]), ("teacher", tid, ["/teacher", f"/class/{cid}"])):
    c2 = app.test_client()
    c2.get("/")
    with c2.session_transaction() as s:
        s["role"], s["uid"] = role, uid
        s[f"{role}_id"] = uid
    for p in pages:
        grab(c2, p)

out = Path(tempfile.gettempdir()) / "nh_strings.json"
out.write_text(json.dumps(list(seen), ensure_ascii=False, indent=1), "utf-8")
print(len(seen), "lines ->", out)
for code in i18n.LANGS:
    if code == "en":
        continue
    missing = [x for x in seen if i18n.tr(x, code) == x]
    print(code, "untranslated:", len(missing))
    for x in missing[:40]:
        print("   ", x)
