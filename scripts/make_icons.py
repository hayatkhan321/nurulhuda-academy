import math, sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
def star(cx, cy, r1, r2, n=8, rot=-90):
    return " ".join(f"{cx+(r1 if k%2==0 else r2)*math.cos(math.radians(rot+k*180/n)):.2f},{cy+(r1 if k%2==0 else r2)*math.sin(math.radians(rot+k*180/n)):.2f}" for k in range(2*n))
def svg(scale, rounded):
    # scale: how big the mark is (maskable icons need ~0.62 to stay in the safe zone)
    r = 'rx="112"' if rounded else ''
    s = scale
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
<defs><radialGradient id="bg" gradientUnits="userSpaceOnUse" cx="256" cy="215" r="384"><stop offset="0" stop-color="#14805f"/><stop offset=".6" stop-color="#0a4a38"/><stop offset="1" stop-color="#03140f"/></radialGradient>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset=".45" stop-color="#e0a63e"/><stop offset=".75" stop-color="#f4d27a"/><stop offset="1" stop-color="#b47c22"/></linearGradient></defs>
<rect width="512" height="512" {r} fill="url(#bg)"/>
<g transform="translate(256 256) scale({s}) translate(-256 -256)">
<rect x="136" y="136" width="240" height="240" fill="none" stroke="url(#g)" stroke-width="20"/>
<rect x="136" y="136" width="240" height="240" fill="none" stroke="url(#g)" stroke-width="20" transform="rotate(45 256 256)"/>
<circle cx="256" cy="256" r="92" fill="none" stroke="url(#g)" stroke-width="6" opacity=".7"/>
<path d="M178 268 Q218 246 256 270 Q294 246 334 268 V330 Q294 308 256 332 Q218 308 178 330 Z" fill="url(#g)"/>
<path d="M256 270 V332" stroke="#0a4a38" stroke-width="6"/>
<circle cx="256" cy="214" r="16" fill="url(#g)"/>
</g></svg>'''
open(f"{out}/icon-master.svg","w").write(svg(1.0, False))
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, size, scale, rounded in [("icon-192.png",192,1.0,False),("icon-512.png",512,1.0,False),
                                        ("icon-maskable-512.png",512,0.72,False),("apple-touch-icon.png",180,0.86,False),
                                        ("favicon-32.png",32,1.15,True)]:
        pg = b.new_page(viewport={"width":size,"height":size})
        pg.set_content('<html><body style="margin:0;background:transparent"><div style="width:%dpx;height:%dpx">%s</div></body></html>' % (size, size, svg(scale,rounded).replace('width="512" height="512"', 'width="100%" height="100%"')))
        pg.screenshot(path=f"{out}/{name}", omit_background=True, clip={"x":0,"y":0,"width":size,"height":size})
    b.close()
