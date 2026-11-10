from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nurulhuda.ledger import aware

# Time zones offered in forms: where families and teachers actually are.
ZONES = [
    ("America/Toronto", "Toronto, Montreal (Eastern)"), ("America/Vancouver", "Vancouver (Pacific)"),
    ("America/Edmonton", "Calgary, Edmonton (Mountain)"), ("America/Winnipeg", "Winnipeg (Central)"),
    ("America/Halifax", "Halifax (Atlantic)"), ("America/New_York", "New York (US Eastern)"),
    ("America/Chicago", "Chicago (US Central)"), ("America/Denver", "Denver (US Mountain)"),
    ("America/Los_Angeles", "Los Angeles (US Pacific)"), ("Europe/London", "London (UK)"),
    ("Europe/Paris", "Central Europe"), ("Asia/Dubai", "Dubai, Abu Dhabi (UAE)"), ("Asia/Riyadh", "Riyadh, Kuwait, Qatar"),
    ("Asia/Karachi", "Pakistan"), ("Asia/Kolkata", "India"), ("Africa/Cairo", "Egypt"), ("Asia/Dhaka", "Bangladesh"),
    ("Asia/Kuala_Lumpur", "Malaysia, Singapore"), ("Australia/Sydney", "Sydney"),
]
ZONE_NAMES = dict(ZONES)


def tz(name):
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local(dt, zone):
    return aware(dt).astimezone(tz(zone)) if dt else None


def _lang():
    try:
        from flask import g
        return getattr(g, "lang", "en")
    except RuntimeError:          # outside a request (e.g. e-mails sent from a script)
        return "en"


def fmt(dt, zone, with_zone=True, lang=None):
    """A class time in the person's own time zone and in the language they are reading the site in."""
    d = local(dt, zone)
    if not d:
        return ""
    lang = lang or _lang()
    zone_label = ZONE_NAMES.get(zone, zone)
    if lang == "en":
        s = d.strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
    else:
        from babel.dates import format_date, format_time
        from nurulhuda.i18n import tr
        s = f"{format_date(d, 'EEE d MMM', locale=lang)}، {format_time(d, 'short', locale=lang)}" if lang in ("ur", "ar") \
            else f"{format_date(d, 'EEE d MMM', locale=lang)}, {format_time(d, 'short', locale=lang)}"
        zone_label = tr(zone_label, lang)
    return f"{s} ({zone_label})" if with_zone else s


def parse_local(date_str, time_str, zone):
    """'2026-11-12', '17:30', 'America/Toronto' -> aware UTC datetime."""
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=tz(zone)).astimezone(timezone.utc)
