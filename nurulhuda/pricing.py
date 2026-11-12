"""Prices, discounts and payment methods, in one place.

How a price is worked out (for each child):
1. The plan's price in the family's currency, times the number of months paid upfront.
2. Discounts are added together: sibling (2nd child, 3rd and later), paying several months upfront, and a code.
3. The total discount is capped (25% by default) so the academy always covers the teacher and its costs.
   A community-rate code may go past the cap.
4. Nothing is ever sold below the floor price per 30 minutes of class, set per currency in the admin area.
   The floor is teacher pay plus payment fees plus a small margin.

Every number here can be changed in the admin area (Packages > Pricing rules) without touching code.
"""
import json
import secrets
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from nurulhuda import db
from nurulhuda.ledger import get_setting
from nurulhuda.models import Invoice, Package, PromoCode

CENT = Decimal("0.01")
SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "C$", "AED": "AED ", "PKR": "Rs ", "EGP": "EGP "}
MONTH_CHOICES = (1, 3, 6, 12)

# Defaults, used until the founders change them in the admin area.
DEFAULTS = {
    "price_currencies": "USD,GBP,EUR,CAD,AED",
    "sibling_2": "10",         # % off the second child's plan
    "sibling_3": "15",         # % off the third child and every child after
    "upfront_3": "5",          # % off when paying 3 months at once
    "upfront_6": "10",
    "upfront_12": "15",
    "max_discount": "25",      # the most any family can get off, all discounts together
    # Lowest price for 30 minutes of class, per currency (teacher pay + fees + margin).
    "floor_prices": "USD:3.25,GBP:2.60,EUR:3.00,CAD:4.50,AED:12.00,PKR:900,EGP:150",
}

# The payment methods families can choose. Their details are filled in from the admin area.
METHODS = {
    "bank": {"name": "Bank transfer", "fields": ("details",),
             "hint": "Account name, bank, IBAN, SWIFT/BIC and the account's currency."},
    "wise": {"name": "Wise", "fields": ("link", "details"),
             "hint": "A Wise payment link, and/or the Wise account details for each currency (USD, GBP, EUR, CAD)."},
    "paypal": {"name": "PayPal", "fields": ("link", "details"),
               "hint": "Your PayPal.Me link (e.g. https://paypal.me/nurulhuda) and/or the PayPal e-mail address."},
}


def setting(key: str) -> str:
    return get_setting(key, DEFAULTS.get(key, ""))


def pct(key: str) -> Decimal:
    try:
        return max(Decimal("0"), min(Decimal("100"), Decimal(setting(key))))
    except Exception:
        return Decimal(DEFAULTS.get(key, "0"))


def currencies() -> list[str]:
    out = [c.strip().upper() for c in setting("price_currencies").split(",") if c.strip()]
    return out or ["USD"]


def floors() -> dict[str, Decimal]:
    out = {}
    for part in setting("floor_prices").split(","):
        if ":" in part:
            cur, val = part.split(":", 1)
            try:
                out[cur.strip().upper()] = Decimal(val.strip())
            except Exception:
                pass
    return out


def money(amount, currency: str) -> str:
    amount = Decimal(amount or 0).quantize(CENT)
    text = f"{amount:,.0f}" if amount == amount.to_integral() else f"{amount:,.2f}"
    sym = SYMBOLS.get(currency, currency + " ")
    return f"{sym}{text}"


def pnum(value) -> str:
    """10.00 -> "10", 12.5 -> "12.5" (Decimal.normalize alone would print 1E+1)."""
    return f"{Decimal(value or 0).normalize():f}"


def upfront_pct(months: int) -> Decimal:
    return pct(f"upfront_{months}") if months in (3, 6, 12) else Decimal("0")


def sibling_pct(position: int) -> Decimal:
    """position 0 = the first (dearest) plan, which is never discounted for siblings."""
    if position == 0:
        return Decimal("0")
    return pct("sibling_2") if position == 1 else pct("sibling_3")


def price_list(currency: str):
    """Public plans for one currency, in display order."""
    return (Package.query.filter_by(currency=currency, active=True, public=True)
            .order_by(Package.sort, Package.classes).all())


def find_package(plan: str, currency: str):
    return Package.query.filter_by(plan=plan, currency=currency, active=True).first()


def check_code(code: str):
    """Return (PromoCode or None, error message or None)."""
    code = (code or "").strip().upper()
    if not code:
        return None, None
    p = PromoCode.query.filter(db.func.upper(PromoCode.code) == code).first()
    if not p or not p.active:
        return None, "That code is not valid."
    if p.expires_on and p.expires_on < date.today():
        return None, "That code has expired."
    if p.max_uses:
        used = Invoice.query.filter(db.func.upper(Invoice.promo_code) == code, Invoice.status != "cancelled").count()
        if used >= p.max_uses:
            return None, "That code has been fully used."
    return p, None


@dataclass
class Line:
    child: str
    package: Package
    base: Decimal                 # price x months
    percent: Decimal              # discount actually given
    total: Decimal
    parts: list = field(default_factory=list)   # e.g. ["Sibling 10%", "3 months upfront 5%"]
    floored: bool = False


@dataclass
class Quote:
    currency: str
    months: int
    lines: list
    code: PromoCode | None = None
    error: str | None = None

    @property
    def subtotal(self):
        return sum((l.base for l in self.lines), Decimal("0"))

    @property
    def total(self):
        return sum((l.total for l in self.lines), Decimal("0"))

    @property
    def discount(self):
        return self.subtotal - self.total

    @property
    def classes(self):
        return sum(l.package.classes * self.months for l in self.lines)


def quote(currency: str, choices: list[tuple[str, str]], months: int = 1, code: str = "") -> Quote:
    """choices: [(child name, plan key), ...]. Unknown plans are skipped."""
    currency = (currency or "USD").upper()
    months = months if months in MONTH_CHOICES else 1
    promo, error = check_code(code)
    picked = []
    for order, (child, plan) in enumerate(choices):
        pkg = find_package(plan, currency)
        if pkg:
            picked.append((order, child, pkg))
    # The dearest plan is paid in full; sibling discounts go on the others.
    picked.sort(key=lambda ocp: ocp[2].price, reverse=True)
    cap = Decimal("100") if promo and promo.beyond_cap else pct("max_discount")
    floor = floors().get(currency)
    lines = []
    for i, (order, child, pkg) in enumerate(picked):
        base = (Decimal(pkg.price) * months).quantize(CENT)
        parts, wanted = [], Decimal("0")
        for label, p in (("Sibling", sibling_pct(i)), (f"{months} months upfront", upfront_pct(months)),
                         (f"Code {promo.code}" if promo else "", Decimal(promo.percent) if promo else Decimal("0"))):
            if p:
                parts.append(f"{label} {pnum(p)}%")
                wanted += p
        given = min(wanted, cap)
        total = (base * (100 - given) / 100).quantize(CENT, ROUND_HALF_UP)
        floored = False
        if floor:
            lowest = (floor * pkg.minutes / 30 * pkg.classes * months).quantize(CENT)
            lowest = min(lowest, base)        # never charge more than the plain price
            if total < lowest:
                total, floored = lowest, True
        percent = ((base - total) / base * 100).quantize(Decimal("0.1")) if base else Decimal("0")
        lines.append((order, Line(child=child, package=pkg, base=base, percent=percent, total=total, parts=parts,
                                  floored=floored or given < wanted)))
    lines = [line for _, line in sorted(lines, key=lambda ol: ol[0])]     # back in the order the family entered
    return Quote(currency=currency, months=months, lines=lines, code=promo, error=error)


def new_number() -> str:
    while True:
        n = f"NH-{secrets.randbelow(900000) + 100000}"
        if not Invoice.query.filter_by(number=n).first():
            return n


def make_invoice(family, q: Quote) -> Invoice:
    inv = Invoice(number=new_number(), family_id=family.id, currency=q.currency, months=q.months, classes=q.classes,
                  subtotal=q.subtotal, discount=q.discount, total=q.total,
                  promo_code=q.code.code if q.code else None,
                  lines=json.dumps([{"child": l.child, "plan": l.package.name, "package_id": l.package.id,
                                     "classes": l.package.classes * q.months, "minutes": l.package.minutes,
                                     "base": str(l.base), "percent": str(l.percent), "total": str(l.total),
                                     "parts": l.parts} for l in q.lines]))
    db.session.add(inv)
    return inv


def invoice_lines(inv: Invoice) -> list[dict]:
    try:
        return json.loads(inv.lines)
    except Exception:
        return []


def methods_on() -> list[dict]:
    """Payment methods that are switched on and have details, in the order the founders prefer."""
    out = []
    for key in setting("pay_order").split(",") if setting("pay_order") else ("bank", "wise", "paypal"):
        key = key.strip()
        if key not in METHODS or get_setting(f"pay_{key}_on", "0") != "1":
            continue
        link, details = get_setting(f"pay_{key}_link", ""), get_setting(f"pay_{key}_details", "")
        if link or details:
            out.append({"key": key, "name": METHODS[key]["name"], "link": link, "details": details})
    return out


def paypal_link(link: str, amount, currency: str) -> str:
    """PayPal.Me links accept the amount and currency on the end, e.g. paypal.me/name/66USD."""
    if "paypal.me/" in link.lower() and link.rstrip("/").count("/") == 3:
        return f"{link.rstrip('/')}/{Decimal(amount).quantize(CENT)}{currency}"
    return link


# The academy's standard price list, used to fill an empty database (Packages > "Load the standard price list").
# 30-minute classes unless stated; a month is 4 weeks of classes.
STANDARD_PLANS = [
    # plan key, name, blurb, classes, minutes, {currency: price}
    ("2-days", "2 days a week", "8 classes of 30 minutes over 4 weeks", 8, 30,
     {"USD": 48, "GBP": 38, "EUR": 44, "CAD": 65, "AED": 175}),
    ("3-days", "3 days a week", "12 classes of 30 minutes over 4 weeks. Our most popular plan", 12, 30,
     {"USD": 66, "GBP": 52, "EUR": 60, "CAD": 90, "AED": 240}),
    ("alternate", "Alternate days", "14 classes of 30 minutes over 4 weeks", 14, 30,
     {"USD": 74, "GBP": 58, "EUR": 68, "CAD": 100, "AED": 270}),
    ("5-days", "5 days a week", "20 classes of 30 minutes over 4 weeks", 20, 30,
     {"USD": 95, "GBP": 75, "EUR": 88, "CAD": 130, "AED": 350}),
    ("hifz", "Hifz, 5 days a week", "20 classes of 60 minutes over 4 weeks, for memorisation", 20, 60,
     {"USD": 180, "GBP": 140, "EUR": 165, "CAD": 245, "AED": 660}),
    ("starter", "15-day starter", "15 daily classes of 30 minutes. A holiday boost or a fresh start", 15, 30,
     {"USD": 79, "GBP": 62, "EUR": 72, "CAD": 108, "AED": 290}),
    ("flexible", "Flexible 10", "10 classes of 30 minutes, on the days you choose. Good for adults", 10, 30,
     {"USD": 60, "GBP": 47, "EUR": 55, "CAD": 82, "AED": 220}),
]


def load_standard_prices() -> int:
    """Add any standard plan/currency that is missing. Never changes prices already set. Returns rows added."""
    added = 0
    for i, (key, name, blurb, classes, minutes, prices) in enumerate(STANDARD_PLANS):
        for cur, price in prices.items():
            if not Package.query.filter_by(plan=key, currency=cur).first():
                db.session.add(Package(plan=key, name=name, blurb=blurb, classes=classes, minutes=minutes,
                                       price=Decimal(price), currency=cur, sort=i * 10, public=True, active=True))
                added += 1
    return added
