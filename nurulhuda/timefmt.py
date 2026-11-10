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


def fmt(dt, zone, with_zone=True):
    d = local(dt, zone)
    if not d:
        return ""
    s = d.strftime("%a %d %b, %I:%M %p").replace(" 0", " ")
    return f"{s} ({ZONE_NAMES.get(zone, zone)})" if with_zone else s


def parse_local(date_str, time_str, zone):
    """'2026-11-12', '17:30', 'America/Toronto' -> aware UTC datetime."""
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=tz(zone)).astimezone(timezone.utc)
