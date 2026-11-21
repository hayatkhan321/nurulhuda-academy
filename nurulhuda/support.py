"""Education support: members buy lessons for children whose families cannot afford them.

How it works
- A member buys "coins". One coin is one 30-minute lesson, at the price the academy sets per currency.
  The purchase is paid like an invoice and gets a normal receipt in the books (it is a sale of lessons).
- Coins sit in the sponsorship wallet, kept apart from the family's own class credits (SponsorEntry).
- A family that cannot afford classes applies privately for a child. An admin approves a number of lessons
  (or rejects), then allocates coins to the child. Coins are taken from members' wallets, oldest first, and the
  child's family receives that many sponsored classes (CreditEntry kind "sponsored", with no money).
- Members see only numbers: children supported, lessons funded, lessons already taught, coins left.
  No child, family or circumstance is ever shown to a member, a teacher or anyone else.

Legal guard rails (UAE Federal Law No. 3 of 2021 regulates the collection of donations; collecting donations from
the public without a permit is an offence). So this is never called a donation or charity, it is not tax-deductible,
and the whole feature stays switched off (Admin > Education support) until the academy has written legal advice.
"""
import secrets
from decimal import Decimal

from sqlalchemy import func

from nurulhuda import books, db, ledger
from nurulhuda.ledger import USES_CREDIT, get_setting, now
from nurulhuda.models import ClassSession, CreditEntry, SponsorEntry, SponsorPurchase, SupportApplication

CENT = Decimal("0.01")
DEFAULTS = {
    "support_on": "0",
    "support_name": "Nurul Huda Education Support Fund",
    "support_who": "diamond",                      # diamond = Diamond members only; all = every family
    "support_lessons_per_child": "12",             # "sponsor one child" = this many lessons (a month of 3 a week)
    "support_packs": "5,10,20",                    # children per pack
    "support_coin_prices": "USD:5.50,GBP:4.35,EUR:5.00,CAD:7.50,AED:20.00",
    "support_max_asked": "48",
}
PURCHASE_STATUS = {"pending": "Waiting for payment", "reported": "Payment being checked", "paid": "Paid", "cancelled": "Cancelled"}
APP_STATUS = {"pending": "Waiting for a decision", "approved": "Approved", "rejected": "Not approved", "closed": "Closed"}


def setting(key: str) -> str:
    return get_setting(key, DEFAULTS[key])


def on() -> bool:
    return setting("support_on") == "1"


def name() -> str:
    return setting("support_name") or DEFAULTS["support_name"]


def lessons_per_child() -> int:
    try:
        return max(1, min(200, int(setting("support_lessons_per_child"))))
    except ValueError:
        return 12


def packs() -> list:
    out = []
    for p in setting("support_packs").split(","):
        try:
            n = int(p.strip())
            if 1 <= n <= 500:
                out.append(n)
        except ValueError:
            pass
    return out or [5, 10, 20]


def coin_prices() -> dict:
    out = {}
    for part in setting("support_coin_prices").split(","):
        if ":" in part:
            cur, val = part.split(":", 1)
            try:
                v = Decimal(val.strip())
                if v > 0:
                    out[cur.strip().upper()] = v
            except Exception:
                pass
    return out


def can_sponsor(family) -> bool:
    if not on() or family is None:
        return False
    return setting("support_who") == "all" or family.membership == "diamond"


# --- buying coins ----------------------------------------------------------------------------------------
def _number() -> str:
    while True:
        n = f"SP-{secrets.randbelow(900000) + 100000}"
        if not SponsorPurchase.query.filter_by(number=n).first():
            return n


def make_purchase(family, coins: int, currency: str):
    price = coin_prices().get((currency or "").upper())
    if not price or coins < 1 or coins > 10000:
        return None
    p = SponsorPurchase(number=_number(), family_id=family.id, coins=coins, currency=currency.upper(),
                        unit_price=price, total=(price * coins).quantize(CENT))
    db.session.add(p)
    db.session.flush()
    books.log("sponsor_purchase_created", "sponsor_purchase", p.id, number=p.number, coins=coins, total=str(p.total),
              currency=p.currency)
    return p


def confirm(p: SponsorPurchase, received: Decimal, rate: Decimal, method: str, note: str = "") -> CreditEntry:
    """The money arrived: a receipt in the books (no classes for the buyer) and coins in the wallet."""
    p.status, p.paid_at, p.amount_received, p.method = "paid", now(), received, method
    entry = CreditEntry(family_id=p.family_id, classes=0, kind="purchase", amount=received, currency=p.currency,
                        method=method, reference=f"{p.number} {p.payer_reference or ''}".strip()[:200],
                        note=f"{name()}: {p.coins} sponsored lesson{'s' if p.coins != 1 else ''} ({p.number})"[:300],
                        receipt_no=books.next_number("RC"), aed_rate=rate, amount_aed=(received * rate).quantize(CENT))
    db.session.add(entry)
    db.session.flush()
    p.credit_entry_id = entry.id
    db.session.add(SponsorEntry(family_id=p.family_id, coins=p.coins, kind="purchase", purchase_id=p.id,
                                note=f"Bought {p.coins} ({p.number})"))
    books.remember_rate(p.currency, rate)
    books.log("sponsor_purchase_paid", "sponsor_purchase", p.id, number=p.number, receipt=entry.receipt_no,
              amount=str(received), currency=p.currency, coins=p.coins, note=note)
    return entry


# --- wallets ---------------------------------------------------------------------------------------------
def donor_balance(family_id) -> int:
    return int(db.session.query(func.coalesce(func.sum(SponsorEntry.coins), 0))
               .filter(SponsorEntry.family_id == family_id).scalar() or 0)


def academy_balance() -> int:
    """Promotional coins the academy itself added (no member behind them)."""
    return int(db.session.query(func.coalesce(func.sum(SponsorEntry.coins), 0))
               .filter(SponsorEntry.family_id.is_(None)).scalar() or 0)


def pool() -> int:
    return int(db.session.query(func.coalesce(func.sum(SponsorEntry.coins), 0)).scalar() or 0)


def allocated_to(app: SupportApplication) -> int:
    return -int(db.session.query(func.coalesce(func.sum(SponsorEntry.coins), 0))
                .filter(SponsorEntry.application_id == app.id, SponsorEntry.kind == "allocate").scalar() or 0)


def taught_for(app: SupportApplication) -> int:
    """Sponsored lessons already used: classes the child had since the first allocation, up to what was allocated."""
    first = (SponsorEntry.query.filter_by(application_id=app.id, kind="allocate")
             .order_by(SponsorEntry.created_at).first())
    if not first:
        return 0
    used = ClassSession.query.filter(ClassSession.student_id == app.student_id, ClassSession.status.in_(USES_CREDIT),
                                     ClassSession.starts_at >= first.created_at).count()
    return min(used, allocated_to(app))


# --- applications ----------------------------------------------------------------------------------------
def open_application(student_id):
    return SupportApplication.query.filter(SupportApplication.student_id == student_id,
                                           SupportApplication.status.in_(("pending", "approved"))).first()


def apply(family, student, lessons: int, reason: str):
    if not on() or student.family_id != family.id or open_application(student.id):
        return None
    try:
        cap = int(setting("support_max_asked"))
    except ValueError:
        cap = 48
    app = SupportApplication(family_id=family.id, student_id=student.id, reason=reason[:3000],
                             lessons_asked=max(1, min(cap, lessons)))
    db.session.add(app)
    db.session.flush()
    books.log("support_applied", "support_application", app.id)      # no reason in the log: it stays private
    return app


def decide(app: SupportApplication, approve: bool, lessons: int, note: str):
    if app.status != "pending":
        return False
    app.status = "approved" if approve else "rejected"
    app.lessons_approved = max(0, min(500, lessons)) if approve else 0
    app.admin_note, app.decided_at = (note or "")[:500] or None, now()
    books.log("support_decided", "support_application", app.id, status=app.status, lessons=app.lessons_approved)
    return True


def allocate(app: SupportApplication, coins: int) -> tuple[int, str | None]:
    """Give approved lessons to the child, taking coins from members' wallets (oldest first), then the academy's."""
    if app.status != "approved":
        return 0, "Only approved applications can receive lessons."
    left = app.lessons_approved - allocated_to(app)
    coins = min(coins, left)
    if coins <= 0:
        return 0, "This application has already received all the lessons approved."
    if coins > pool():
        return 0, f"Only {pool()} coins are in the sponsorship wallet."
    need = coins
    donors = (db.session.query(SponsorEntry.family_id, func.min(SponsorEntry.created_at), func.sum(SponsorEntry.coins))
              .group_by(SponsorEntry.family_id).all())
    donors.sort(key=lambda d: (d[0] is None, ledger.aware(d[1])))        # members first, oldest first; academy last
    for fid, _, bal in donors:
        bal = int(bal or 0)
        if need <= 0 or bal <= 0:
            continue
        take = min(bal, need)
        db.session.add(SponsorEntry(family_id=fid, coins=-take, kind="allocate", application_id=app.id,
                                    note=f"Sponsored lessons for application {app.id}"))
        need -= take
    db.session.add(CreditEntry(family_id=app.family_id, classes=coins, kind="sponsored",
                               note=f"{coins} sponsored lesson{'s' if coins != 1 else ''} for {app.student.first_name}"))
    books.log("support_allocated", "support_application", app.id, coins=coins)
    return coins, None


def add_promo(coins: int, note: str):
    db.session.add(SponsorEntry(family_id=None, coins=coins, kind="promo", note=(note or "Academy's own lessons")[:300]))
    books.log("support_promo_added", None, None, coins=coins, note=note)


# --- what members and admins see -------------------------------------------------------------------------
def donor_view(family) -> dict:
    entries = SponsorEntry.query.filter_by(family_id=family.id).all()
    bought = sum(e.coins for e in entries if e.kind == "purchase")
    funded = -sum(e.coins for e in entries if e.kind == "allocate")
    apps = {}
    for e in entries:
        if e.kind == "allocate" and e.application_id:
            apps[e.application_id] = apps.get(e.application_id, 0) - e.coins
    taught = 0
    for aid, mine in apps.items():
        app = db.session.get(SupportApplication, aid)
        total = allocated_to(app) if app else 0
        if total:
            taught += round(taught_for(app) * mine / total)
    return {"bought": bought, "funded": funded, "children": len(apps), "taught": taught,
            "balance": donor_balance(family.id),
            "purchases": SponsorPurchase.query.filter_by(family_id=family.id).order_by(SponsorPurchase.created_at.desc()).limit(10).all()}


def report() -> dict:
    apps = SupportApplication.query.all()
    allocated = {a.id: allocated_to(a) for a in apps}
    return {"pool": pool(), "academy": academy_balance(),
            "bought": int(db.session.query(func.coalesce(func.sum(SponsorEntry.coins), 0)).filter(SponsorEntry.kind == "purchase").scalar() or 0),
            "allocated": sum(allocated.values()), "taught": sum(taught_for(a) for a in apps if allocated[a.id]),
            "children": sum(1 for a in apps if allocated[a.id]), "pending": sum(1 for a in apps if a.status == "pending"),
            "allocated_by_app": allocated}
