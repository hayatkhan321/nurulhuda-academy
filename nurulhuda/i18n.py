"""Site languages.

Pages are written in English. After a page is rendered, every piece of visible text is looked up in the
catalogue for the visitor's language (nurulhuda/i18n/<code>.json, English text -> translation). Anything not
yet translated simply stays in English, so a missing line never breaks a page.

The English lines are numbered in i18n/keys.json (run scripts/i18n_extract.py to find new ones); each language
file maps those numbers to its translation.

The language is chosen in this order: ?lang= in the address, the visitor's saved choice (a cookie),
then the languages their phone or browser asks for, and finally English.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from flask import g, request

# Wrap anything that must never be translated in <!--nt--> ... <!--/nt-->.
# code: (name in its own language, English name, right-to-left)
LANGS = {
    "en": ("English", "English", False),
    "ur": ("اردو", "Urdu", True),
    "ar": ("العربية", "Arabic", True),
    "hi": ("हिन्दी", "Hindi", False),
    "ms": ("Bahasa Melayu", "Malay", False),
    "id": ("Bahasa Indonesia", "Indonesian", False),
    "es": ("Español", "Spanish", False),
    "fr": ("Français", "French", False),
}
COOKIE = "nh_lang"
DIR = Path(__file__).with_name("i18n")
SKIP_PREFIXES = ("/admin", "/static", "/sw.js", "/manifest.webmanifest", "/health", "/robots.txt", "/sitemap.xml")


def pick_lang() -> str:
    asked = (request.args.get("lang") or "").lower()
    if asked in LANGS:
        return asked
    saved = request.cookies.get(COOKIE, "")
    if saved in LANGS:
        return saved
    # "ms" and "id" are close; Accept-Language may also say "ur-PK", "fr-CA", "es-419" ...
    best = request.accept_languages.best_match(list(LANGS), default="en")
    return best or "en"


@lru_cache(maxsize=None)
def catalogue(code: str) -> tuple[dict, list]:
    """Plain lines, plus lines with {placeholders} (e.g. "{n} classes left") turned into patterns."""
    path = DIR / f"{code}.json"
    if code == "en" or not path.exists():
        return {}, []
    # keys.json numbers every English line; <code>.json gives the translation for each number.
    keys = json.loads((DIR / "keys.json").read_text("utf-8"))
    data = {keys[n]: text for n, text in json.loads(path.read_text("utf-8")).items() if n in keys}
    plain, patterns = {}, []
    for src, dst in data.items():
        if not dst:
            continue
        src = " ".join(src.split())
        if "{" in src and re.search(r"\{\w+\}", src):
            names = re.findall(r"\{(\w+)\}", src)
            rx = "^" + re.sub(r"\\\{(\w+)\\\}", lambda m: f"(?P<{m.group(1)}>.+?)", re.escape(src)) + "$"
            patterns.append((re.compile(rx), dst, names))
        else:
            plain[src] = dst
    return plain, patterns


def tr(text: str, code: str | None = None) -> str:
    """Translate one line (used in Python code and templates); falls back to the English text."""
    code = code or getattr(g, "lang", "en")
    if code == "en" or not text:
        return text
    key = " ".join(text.split())
    plain, patterns = catalogue(code)
    if key in plain:
        return plain[key]
    for rx, dst, names in patterns:
        m = rx.match(key)
        if m:
            out = dst
            for n in names:
                out = out.replace("{" + n + "}", tr(m.group(n), code))
            return out
    return text


_BLOCK = re.compile(r"(<!--nt-->.*?<!--/nt-->|<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->)", re.S | re.I)
_TEXT = re.compile(r">([^<>]+)<")
_ATTR = re.compile(r'(\s(?:placeholder|aria-label|title|alt)=")([^"]+)(")')
_META = re.compile(r'(<meta\s+(?:name="description"|property="og:(?:title|description)")\s+content=")([^"]+)(")')
_TITLE = re.compile(r"(<title>)(.*?)(</title>)", re.S)


def _swap_text(m, code):
    raw = m.group(1)
    core = raw.strip()
    if not core or not re.search(r"[A-Za-z]", core):
        return m.group(0)
    import html as _h
    plain = _h.unescape(core)
    out = tr(plain, code)
    if out == plain:
        return m.group(0)
    lead = raw[: len(raw) - len(raw.lstrip())]
    trail = raw[len(raw.rstrip()):]
    return ">" + lead + _h.escape(out, quote=False) + trail + "<"


def _swap_attr(m, code):
    import html as _h
    plain = _h.unescape(m.group(2))
    out = tr(plain, code)
    return m.group(0) if out == plain else m.group(1) + _h.escape(out) + m.group(3)


def _swap_title(m, code):
    import html as _h
    parts = [p.strip() for p in _h.unescape(m.group(2)).split(" | ")]
    return m.group(1) + _h.escape(" | ".join(tr(p, code) for p in parts), quote=False) + m.group(3)


def translate_html(page: str, code: str) -> str:
    if code == "en":
        return page
    pieces = _BLOCK.split(page)
    for i, piece in enumerate(pieces):
        if i % 2:          # script, style, textarea or comment: leave untouched
            continue
        piece = _TITLE.sub(lambda m: _swap_title(m, code), piece)
        piece = _META.sub(lambda m: _swap_attr(m, code), piece)
        piece = _ATTR.sub(lambda m: _swap_attr(m, code), piece)
        piece = _TEXT.sub(lambda m: _swap_text(m, code), piece)
        pieces[i] = piece
    return "".join(pieces)


def collect_strings(page: str) -> list[str]:
    """Every visible English line on a page (used by scripts/i18n_extract.py)."""
    import html as _h
    found = []
    for i, piece in enumerate(_BLOCK.split(page)):
        if i % 2:
            continue
        for m in _TITLE.finditer(piece):
            found += [p.strip() for p in _h.unescape(m.group(2)).split(" | ")]
        for rx in (_META, _ATTR):
            found += [_h.unescape(m.group(2)) for m in rx.finditer(piece)]
        for m in _TEXT.finditer(piece):
            core = " ".join(_h.unescape(m.group(1)).split())
            if core and re.search(r"[A-Za-z]", core):
                found.append(core)
    return found


def init_app(app):
    @app.before_request
    def _choose_language():
        # The admin area is for the founders and stays in English, left to right.
        g.lang = "en" if request.path.startswith(SKIP_PREFIXES) else pick_lang()

    @app.after_request
    def _apply_language(resp):
        code = getattr(g, "lang", "en")
        if request.args.get("lang", "").lower() in LANGS:
            resp.set_cookie(COOKIE, code, max_age=60 * 60 * 24 * 365, samesite="Lax",
                            secure=app.config.get("IS_PRODUCTION", False))
        resp.headers.add("Vary", "Cookie")
        resp.headers.add("Vary", "Accept-Language")
        if (code != "en" and resp.mimetype == "text/html" and not resp.direct_passthrough
                and not request.path.startswith(SKIP_PREFIXES)):
            resp.set_data(translate_html(resp.get_data(as_text=True), code))
        return resp

    @app.context_processor
    def _language_context():
        code = getattr(g, "lang", "en")
        return {"lang": code, "lang_dir": "rtl" if LANGS[code][2] else "ltr", "LANGS": LANGS, "t": tr}
