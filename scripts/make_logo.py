"""Draw the Nurul Huda logo: a faceted gold Rub el Hizb (eight-point star) around an emerald centre with an
open Quran and a point of light. Writes the inline header logo, a standalone SVG, and the app icons.

    python scripts/make_logo.py            # writes into nurulhuda/templates and nurulhuda/static
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIGHT = math.radians(-135)          # light comes from the top left


def pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def mix(c1, c2, t):
    c1 = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    c2 = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(c1, c2))


def gold(b):
    """b from 0 (shadow) to 1 (highlight)."""
    stops = [(0, "#6b420a"), (0.35, "#b5781f"), (0.6, "#e2ad48"), (0.82, "#f7d983"), (1, "#fff6d2")]
    for (t1, c1), (t2, c2) in zip(stops, stops[1:]):
        if b <= t2:
            return mix(c1, c2, (b - t1) / (t2 - t1))
    return stops[-1][1]


def shade(normal_deg, lift=0.0):
    return max(0.0, min(1.0, 0.5 + 0.5 * math.cos(math.radians(normal_deg) - LIGHT) * 0.9 + lift))


def facets(cx, cy, r_out, r_in, rot, lift=0.0):
    """An eight-point star split into 16 facets, each half of a point shaded by which way it faces."""
    out = []
    for k in range(8):
        a_p = rot + k * 45
        p = pt(cx, cy, r_out, a_p)
        v1 = pt(cx, cy, r_in, a_p - 22.5)
        v2 = pt(cx, cy, r_in, a_p + 22.5)
        for v, side in ((v1, -1), (v2, 1)):
            b = shade(a_p + side * 55, lift)
            out.append(f'<path d="M{cx:.2f} {cy:.2f}L{v[0]:.2f} {v[1]:.2f}L{p[0]:.2f} {p[1]:.2f}Z" fill="{gold(b)}"/>')
    return "".join(out)


def star_path(cx, cy, r_out, r_in, rot):
    pts = []
    for k in range(16):
        r = r_out if k % 2 == 0 else r_in
        pts.append(pt(cx, cy, r, rot + k * 22.5))
    return "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts) + "Z"


def mark(uid="nh", shadow=True, simple=False):
    """The logo on a 200x200 canvas, transparent background."""
    c = 100
    f = []
    f.append(f'''<defs>
<radialGradient id="{uid}-em" cx="42%" cy="36%" r="70%"><stop offset="0" stop-color="#1f9a73"/><stop offset=".55" stop-color="#0b5d45"/><stop offset="1" stop-color="#032a1f"/></radialGradient>
<linearGradient id="{uid}-ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff3c4"/><stop offset=".3" stop-color="#e6b04c"/><stop offset=".62" stop-color="#9c6516"/><stop offset=".85" stop-color="#e9bd5e"/><stop offset="1" stop-color="#7a4b0c"/></linearGradient>
<linearGradient id="{uid}-ring2" x1="1" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff3c4"/><stop offset=".45" stop-color="#d49a36"/><stop offset="1" stop-color="#6b420a"/></linearGradient>
<linearGradient id="{uid}-book" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff6d2"/><stop offset=".55" stop-color="#f1c863"/><stop offset="1" stop-color="#b5781f"/></linearGradient>
<radialGradient id="{uid}-noor" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffffff"/><stop offset=".35" stop-color="#fff2b8"/><stop offset="1" stop-color="#ffd76a" stop-opacity="0"/></radialGradient>
<radialGradient id="{uid}-spec" cx="28%" cy="18%" r="45%"><stop offset="0" stop-color="#ffffff" stop-opacity=".28"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<filter id="{uid}-sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity=".45"/></filter>
<filter id="{uid}-in" x="-10%" y="-10%" width="120%" height="120%"><feOffset dx="0" dy="3"/><feGaussianBlur stdDeviation="3" result="o"/><feComposite in="SourceGraphic" in2="o" operator="arithmetic" k2="-1" k3="1" result="s"/><feFlood flood-color="#000" flood-opacity=".55"/><feComposite in2="s" operator="in"/><feComposite in2="SourceGraphic" operator="over"/></filter>
</defs>''')
    g_open = f'<g filter="url(#{uid}-sh)">' if shadow else "<g>"
    f.append(g_open)
    # Outer bevelled ring
    f.append(f'<circle cx="{c}" cy="{c}" r="96" fill="url(#{uid}-ring)"/>')
    f.append(f'<circle cx="{c}" cy="{c}" r="89" fill="url(#{uid}-ring2)"/>')
    f.append(f'<circle cx="{c}" cy="{c}" r="85" fill="url(#{uid}-em)"/>')
    # Eight small gold studs between the points, on the emerald field
    for k in ([] if simple else range(8)):
        x, y = pt(c, c, 72, -90 + 22.5 + k * 45)
        f.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{gold(shade(-90 + 22.5 + k * 45, 0.1))}" stroke="#5a3606" stroke-width=".6" stroke-opacity=".5"/>')
    # The Rub el Hizb: two squares at 45 degrees, faceted so each point has a lit and a shaded side
    r_out = 84
    r_in = r_out * math.cos(math.radians(45)) / math.cos(math.radians(22.5))
    f.append(facets(c, c, r_out, r_in, -90, lift=0.02))
    f.append(f'<path d="{star_path(c, c, r_out, r_in, -90)}" fill="none" stroke="#4a2c04" stroke-width="1.4" stroke-opacity=".6" stroke-linejoin="round"/>')
    # Inner bevel line along the star, a thin bright edge
    if not simple:
        f.append(f'<path d="{star_path(c, c, r_out - 6, r_in - 5, -90)}" fill="none" stroke="#fff4c8" stroke-width=".8" stroke-opacity=".45" stroke-linejoin="round"/>')
    # Emerald centre, sunk into the star
    f.append(f'<circle cx="{c}" cy="{c}" r="40" fill="url(#{uid}-ring)"/>')
    f.append(f'<circle cx="{c}" cy="{c}" r="36" fill="url(#{uid}-em)" filter="url(#{uid}-in)"/>')
    if not simple:
        # Open Quran
        f.append(f'<path d="M72 108 Q86 99 100 108 Q114 99 128 108 L128 128 Q114 119 100 128 Q86 119 72 128 Z" fill="url(#{uid}-book)" stroke="#6b420a" stroke-width="1.1"/>')
        f.append('<path d="M100 108 V128" stroke="#6b420a" stroke-width="1.6"/>')
        f.append('<path d="M77 113 Q87 107 96 112 M77 118 Q87 112 96 117 M104 112 Q113 107 123 113 M104 117 Q113 112 123 118" fill="none" stroke="#9c6516" stroke-width=".9" opacity=".7"/>')
    # Light (Noor) rising from the book
    ny, nr = (100, 13) if simple else (86, 5.2)
    f.append(f'<circle cx="{c}" cy="{ny}" r="{nr * 3.3:.1f}" fill="url(#{uid}-noor)"/>')
    f.append(f'<circle cx="{c}" cy="{ny}" r="{nr}" fill="#fffbe8"/>')
    # Specular highlight across the whole medallion
    f.append(f'<circle cx="{c}" cy="{c}" r="96" fill="url(#{uid}-spec)"/>')
    f.append("</g>")
    return "".join(f)


def standalone(size=200, bg=None, scale=1.0, rounded=False, simple=False):
    inner = mark("nh", simple=simple)
    bg_svg = ""
    if bg:
        rx = f' rx="{44 if rounded else 0}"'
        bg_svg = (f'<defs><radialGradient id="bgg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="#14805f"/>'
                  f'<stop offset=".6" stop-color="#0a4a38"/><stop offset="1" stop-color="#03140f"/></radialGradient></defs>'
                  f'<rect width="200" height="200"{rx} fill="url(#bgg)"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="{size}" height="{size}">{bg_svg}'
            f'<g transform="translate(100 100) scale({scale}) translate(-100 -100)">{inner}</g></svg>')


if __name__ == "__main__":
    tpl = ROOT / "nurulhuda" / "templates" / "_logo.html"
    tpl.write_text('<svg class="logo" viewBox="0 0 200 200" aria-hidden="true">' + mark("nhl") + "</svg>\n", "utf-8")
    (ROOT / "nurulhuda" / "static" / "img" / "logo.svg").write_text(standalone(512), "utf-8")
    (ROOT / "nurulhuda" / "static" / "img" / "icon.svg").write_text(standalone(200, bg=True, scale=0.86, rounded=True), "utf-8")
    from playwright.sync_api import sync_playwright
    icons = ROOT / "nurulhuda" / "static" / "icons"
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size, scale, rounded in [("icon-192.png", 192, 0.86, False), ("icon-512.png", 512, 0.86, False),
                                            ("icon-maskable-512.png", 512, 0.66, False), ("apple-touch-icon.png", 180, 0.84, False),
                                            ("favicon-32.png", 32, 1.0, True)]:
            pg = b.new_page(viewport={"width": size, "height": size})
            svg = standalone(size, bg=True, scale=scale, rounded=rounded, simple=size <= 32)
            pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            pg.screenshot(path=str(icons / name), omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
        b.close()
    print("logo written")
