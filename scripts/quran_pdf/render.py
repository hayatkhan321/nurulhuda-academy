import sys, time
from playwright.sync_api import sync_playwright
code = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(); pg.set_default_timeout(0)
    t = time.time()
    out = __import__("pathlib").Path(__file__).parent / "out"
    pg.goto(f"file://{out}/quran-{code}.html", wait_until="load", timeout=600000)
    pg.evaluate("document.fonts.ready")
    footer = "<div style='width:100%;font-size:8pt;color:#666;text-align:center;font-family:serif'><span class='pageNumber'></span></div>"
    pg.pdf(path=str(out / f"quran-{code}.pdf"), format="A4", print_background=True, prefer_css_page_size=True,
           display_header_footer=True, header_template="<div></div>", footer_template=footer,
           outline=True, tagged=False)
    print(code, "done in", round(time.time() - t), "s")
    b.close()
