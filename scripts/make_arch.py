"""Generates the embossed gilded mihrab arch used on the home page."""
import math

def arch(xl, xr, ys, apex_y, bottom):
    mid = (xl + xr) / 2
    h = ys - apex_y
    half = (xr - xl) / 2
    # centre of the left arc lies on the springing line, to the right of xl
    cx = (mid**2 - xl**2 + h**2) / (2 * (mid - xl))
    r = cx - xl
    return (f"M{xl:.1f} {bottom} V{ys} A{r:.1f} {r:.1f} 0 0 1 {mid:.1f} {apex_y:.1f} "
            f"A{r:.1f} {r:.1f} 0 0 1 {xr:.1f} {ys} V{bottom}")

W, H = 400, 500
B = 452   # bottom of opening
rings = []
for i, d in enumerate([34, 24, 15, 7]):
    rings.append(arch(100 - d, 300 + d, 236, 92 - d * 1.15, B))
opening = arch(100, 300, 236, 92, B) + " Z"
inner = arch(112, 288, 238, 108, B)

def star(cx, cy, r1, r2, n=8, rot=-90):
    pts = []
    for k in range(2 * n):
        a = math.radians(rot + k * 180 / n)
        r = r1 if k % 2 == 0 else r2
        pts.append(f"{cx + r*math.cos(a):.1f},{cy + r*math.sin(a):.1f}")
    return " ".join(pts)

svg = f'''<svg class="arch" viewBox="0 0 {W} {H}" role="img" aria-label="Golden Islamic arch with the words Nurul Huda in Arabic calligraphy">
  <defs>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff2bf"/><stop offset=".22" stop-color="#e9b84d"/>
      <stop offset=".48" stop-color="#9a6716"/><stop offset=".7" stop-color="#f4d074"/>
      <stop offset="1" stop-color="#a5711b"/>
    </linearGradient>
    <linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffe9a6"/><stop offset=".5" stop-color="#c88f2c"/><stop offset="1" stop-color="#7d5110"/>
    </linearGradient>
    <radialGradient id="recess" cx=".5" cy=".42" r=".7">
      <stop offset="0" stop-color="#14805f"/><stop offset=".6" stop-color="#0a4a38"/><stop offset="1" stop-color="#04241b"/>
    </radialGradient>
    <pattern id="spandrel" width="18" height="18" patternUnits="userSpaceOnUse">
      <rect width="18" height="18" fill="#0a4a38"/>
      <polygon points="{star(9, 9, 7.5, 3.4)}" fill="none" stroke="#e7b54a" stroke-width=".9" stroke-opacity=".75"/>
    </pattern>
    <filter id="emboss" x="-15%" y="-15%" width="130%" height="130%" color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="blur"/>
      <feSpecularLighting in="blur" surfaceScale="3.2" specularConstant=".95" specularExponent="20" lighting-color="#fff7da" result="spec">
        <feDistantLight azimuth="235" elevation="40"/>
      </feSpecularLighting>
      <feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn"/>
      <feComposite in="SourceGraphic" in2="specIn" operator="arithmetic" k1="0" k2="1" k3=".9" k4="0" result="lit"/>
      <feGaussianBlur in="SourceAlpha" stdDeviation="2.4" result="sb"/>
      <feOffset in="sb" dx="2.5" dy="4" result="so"/>
      <feFlood flood-color="#011a12" flood-opacity=".55"/>
      <feComposite in2="so" operator="in" result="shadow"/>
      <feMerge><feMergeNode in="shadow"/><feMergeNode in="lit"/></feMerge>
    </filter>
    <filter id="inset" x="-5%" y="-5%" width="110%" height="110%">
      <feFlood flood-color="#000" flood-opacity=".6"/>
      <feComposite in2="SourceAlpha" operator="out"/>
      <feGaussianBlur stdDeviation="7"/><feOffset dx="0" dy="6" result="ish"/>
      <feComposite in="ish" in2="SourceAlpha" operator="in" result="inner"/>
      <feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="inner"/></feMerge>
    </filter>
    <clipPath id="frameClip"><rect x="40" y="22" width="320" height="438"/></clipPath>
  </defs>

  <!-- alfiz frame with geometric spandrels -->
  <g filter="url(#emboss)">
    <rect x="40" y="22" width="320" height="438" rx="3" fill="url(#gold)"/>
  </g>
  <rect x="50" y="32" width="300" height="428" fill="url(#spandrel)"/>

  <!-- stepped arch mouldings -->
  <g filter="url(#emboss)" fill="none">
    {"".join(f'<path d="{d}" stroke="url(#gold)" stroke-width="{w}"/>' for d, w in zip(rings, [7, 5, 6, 4]))}
  </g>
  <!-- pearl moulding -->
  <path d="{rings[3]}" fill="none" stroke="#fff0c2" stroke-width="3.2" stroke-linecap="round" stroke-dasharray="0 7.5" opacity=".9"/>

  <!-- the recess -->
  <path d="{opening}" fill="url(#recess)" filter="url(#inset)"/>
  <path d="{inner}" fill="none" stroke="#e7b54a" stroke-opacity=".35" stroke-width="1.2"/>

  <!-- crown medallion -->
  <g filter="url(#emboss)">
    <polygon points="{star(200, 166, 26, 12.5)}" fill="url(#gold)"/>
    <circle cx="200" cy="166" r="7" fill="#0a4a38"/>
    <circle cx="200" cy="166" r="3.2" fill="url(#gold)"/>
  </g>

  <!-- calligraphy -->
  <text x="200" y="306" text-anchor="middle" direction="rtl" font-family="Amiri, 'Noto Naskh Arabic', serif" font-weight="700"
        font-size="50" fill="url(#goldV)" filter="url(#emboss)" lang="ar">نور الهدى</text>
  <text x="200" y="340" text-anchor="middle" font-family="'Bricolage Grotesque', system-ui, sans-serif" font-size="13"
        fill="#e9d6a0" letter-spacing=".5">Light of guidance</text>

  <!-- columns, capitals and plinth -->
  <g filter="url(#emboss)">
    <rect x="80" y="244" width="14" height="208" rx="3" fill="url(#goldV)"/>
    <rect x="306" y="244" width="14" height="208" rx="3" fill="url(#goldV)"/>
    <path d="M74 236 h26 l-4 10 h-18 z" fill="url(#gold)"/>
    <path d="M300 236 h26 l-4 10 h-18 z" fill="url(#gold)"/>
    <rect x="30" y="456" width="340" height="12" rx="2" fill="url(#gold)"/>
    <rect x="20" y="468" width="360" height="14" rx="2" fill="url(#goldV)"/>
  </g>
</svg>'''
print(svg)
