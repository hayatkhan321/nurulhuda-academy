"""Nurul Huda Academy short videos (Reels / Shorts / TikTok): 1080x1920, 30 fps, motion graphics drawn as HTML pages.

    python3 reel.py specs/how-it-works.json            # build the video (and a small copy for Google Drive)
    python3 reel.py specs/how-it-works.json --preview  # one still per scene, to check the layout first

A spec is JSON: {"slug": ..., "voice": "narration.mp3" (optional), "greeting": true, "scenes": [...]}.
Each scene has a "kind" (see BODY below) and a "sub" (the on-screen caption, always shown, so the video works muted).

Sound: the optional narration (Alice), opened by Dr Hayat's own recorded "Assalamu alaikum" when "greeting" is true,
plus a soft whoosh at each cut. Never music, never recitation. Without a voice file the video is caption-only.
Read README.md before making a video: it has the rules.
"""
import html, json, os, random, re, subprocess, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
A = os.path.join(HERE, "assets")
W, H, FPS = 1080, 1920, 30
TAIL = 2.2          # hold the last scene this long after the voice ends
GAP_AFTER_GREETING = 0.35
LOGO = open(os.path.join(A, "logo.svg.html")).read()
HAFS_FONT = os.path.join(REPO, "public", "quran", "hafs.18.woff2")
HAFS_DATA = os.path.join(REPO, "public", "quran", "hafs-v18.json")


def asset(name):
    """An image from assets/ (or any absolute path) as a file:// URL."""
    p = name if os.path.isabs(name) else os.path.join(A, name)
    if not os.path.exists(p):
        sys.exit(f"missing image: {p}")
    return "file://" + p


# ---------- verified Quran text (King Fahd Complex, Uthmanic Hafs v18), never typed by hand ----------
_HAFS = None


def ayat(surah, first, last=None):
    """The Arabic of surah:first..last exactly as in the King Fahd data the lesson board uses."""
    global _HAFS
    if _HAFS is None:
        _HAFS = {(s, a): t for page in json.load(open(HAFS_DATA))["pages"] for s, a, t in page}
    last = last or first
    out = [_HAFS.get((surah, a)) for a in range(first, last + 1)]
    if None in out:
        sys.exit(f"verse not found: {surah}:{first}-{last}")
    return " ".join(out)


EDITIONS = {"eng-ummmuhammad": "Sahih International", "urd-muhammadjunagar": "Muhammad Junagarhi"}


def translation(surah, first, last=None, edition="eng-ummmuhammad"):
    """A published translation fetched from the quran-api text on GitHub (never written by us)."""
    import urllib.request
    parts = []
    for a in range(first, (last or first) + 1):
        url = f"https://raw.githubusercontent.com/fawazahmed0/quran-api/1/editions/{edition}/{surah}/{a}.json"
        with urllib.request.urlopen(url, timeout=20) as r:
            parts.append(json.load(r)["text"].strip())
    return " ".join(parts), EDITIONS.get(edition, edition)


random.seed(7)
PARTICLES = "".join(
    f'<i style="left:{random.uniform(0,100):.1f}%;top:{random.uniform(0,100):.1f}%;width:{(s:=random.uniform(3,9)):.1f}px;height:{s:.1f}px;'
    f'animation-duration:{random.uniform(5,11):.1f}s;animation-delay:-{random.uniform(0,10):.1f}s;opacity:{random.uniform(.25,.8):.2f}"></i>'
    for _ in range(46))

STAR = ('<svg class="tess" viewBox="0 0 400 400"><defs><pattern id="p" width="100" height="100" patternUnits="userSpaceOnUse">'
        '<path d="M50 8 L61 39 L92 50 L61 61 L50 92 L39 61 L8 50 L39 39Z M50 22 L70 30 L78 50 L70 70 L50 78 L30 70 L22 50 L30 30Z" '
        'fill="none" stroke="#e9bd5e" stroke-width="1.3"/><circle cx="0" cy="0" r="6" fill="none" stroke="#e9bd5e" stroke-width="1"/>'
        '<circle cx="100" cy="100" r="6" fill="none" stroke="#e9bd5e" stroke-width="1"/></pattern></defs>'
        '<rect width="400" height="400" fill="url(#p)"/></svg>')

CSS = """
@font-face{font-family:B;src:url(file://%(A)s/brico.woff2) format('woff2');font-weight:200 800}
@font-face{font-family:N;src:url(file://%(A)s/nast.woff2) format('woff2')}
@font-face{font-family:Hafs;src:url(file://%(HAFS)s) format('woff2')}
*{box-sizing:border-box;margin:0}
html,body{width:1080px;height:1920px;overflow:hidden}
body{font-family:B,sans-serif;color:#fff;background:radial-gradient(ellipse at 50%% 22%%,#15845f 0%%,#08402f 46%%,#021a13 100%%);position:relative;perspective:1600px}
.tess{position:absolute;width:2600px;height:2600px;left:-760px;top:-340px;opacity:.12;animation:spin 40s linear both}
@keyframes spin{from{transform:rotate(0) scale(1)}to{transform:rotate(12deg) scale(1.08)}}
.rays{position:absolute;left:50%%;top:-300px;width:2400px;height:2400px;margin-left:-1200px;opacity:.16;
 background:repeating-conic-gradient(from 0deg at 50%% 50%%,rgba(255,236,170,.55) 0deg 4deg,transparent 4deg 16deg);
 -webkit-mask:radial-gradient(circle at 50%% 50%%,#000 0,transparent 55%%);mask:radial-gradient(circle at 50%% 50%%,#000 0,transparent 55%%);animation:rays 30s linear both}
@keyframes rays{from{transform:rotate(0)}to{transform:rotate(25deg)}}
.pts i{position:absolute;border-radius:50%%;background:radial-gradient(circle,#fff6d0,#e3a237 60%%,transparent 70%%);animation:float linear infinite}
@keyframes float{0%%{transform:translateY(40px)}100%%{transform:translateY(-220px)}}
.glow{position:absolute;left:50%%;top:38%%;width:900px;height:900px;margin:-450px 0 0 -450px;border-radius:50%%;
 background:radial-gradient(circle,rgba(255,215,120,.22),transparent 65%%);animation:pulse 4s ease-in-out infinite alternate}
@keyframes pulse{from{transform:scale(.9);opacity:.7}to{transform:scale(1.1);opacity:1}}
.top{position:absolute;top:110px;left:0;right:0;display:flex;align-items:center;justify-content:center;gap:20px;z-index:3}
.top svg{width:84px;height:84px}.top b{font-size:38px;font-weight:700;letter-spacing:-.5px}
.top span{display:block;color:#f2c25b;font-family:N;font-size:28px;line-height:1.6}
.stage{position:absolute;left:0;right:0;top:225px;height:1080px;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2}
h1{font-size:96px;line-height:1.02;letter-spacing:-3px;font-weight:780;text-align:center;padding:0 70px;text-shadow:0 8px 40px rgba(0,0,0,.35)}
h1 em{font-style:normal;color:#f7cf6a}
.ur{font-family:N;direction:rtl;text-align:center;font-size:50px;line-height:2;color:#f2c25b;margin-top:14px;padding:0 60px}
.kicker{font-size:40px;font-weight:650;letter-spacing:.5px;color:#f7cf6a;background:rgba(0,0,0,.25);border:2px solid rgba(247,207,106,.5);padding:10px 28px;border-radius:50px;margin-bottom:34px}
.in{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}.pop{animation:pop .7s cubic-bezier(.3,1.6,.5,1) both}
.d1{animation-delay:.3s}.d2{animation-delay:.7s}.d3{animation-delay:1.1s}.d4{animation-delay:1.5s}.d5{animation-delay:1.9s}.d6{animation-delay:2.3s}
@keyframes rise{from{opacity:0;transform:translateY(80px)}to{opacity:1;transform:none}}
@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}
.arch{width:500px;height:612px;position:relative;display:flex;align-items:center;justify-content:center}
.arch svg.frame{position:absolute;inset:0;width:100%%;height:100%%}
.arch path{fill:none;stroke:url(#gold);stroke-width:7;stroke-dasharray:3000;stroke-dashoffset:3000;animation:draw 2.2s ease-out both}
.arch path.in2{stroke-width:2.5;opacity:.7;animation-delay:.5s}
@keyframes draw{to{stroke-dashoffset:0}}
.arch .lg{width:270px;height:270px;animation:logo 1.6s cubic-bezier(.2,.9,.3,1.2) .6s both;filter:drop-shadow(0 20px 50px rgba(0,0,0,.5))}
.lg svg{width:100%%;height:100%%}
@keyframes logo{from{opacity:0;transform:scale(.3) rotate(-30deg)}to{opacity:1;transform:none}}
.phone{width:430px;height:880px;border-radius:64px;background:#0b1512;padding:16px;box-shadow:0 50px 120px rgba(0,0,0,.55),0 0 0 3px rgba(247,207,106,.45);
 overflow:hidden;animation:phone 1.1s cubic-bezier(.2,.8,.2,1) both;transform-origin:50%% 60%%}
.phone img{width:100%%;height:100%%;object-fit:cover;object-position:top;border-radius:50px;display:block;animation:scroll 6s ease-in-out .9s both}
@keyframes phone{from{opacity:0;transform:translateY(300px) rotateX(25deg) rotateY(-18deg)}to{opacity:1;transform:rotateY(-6deg)}}
@keyframes scroll{from{object-position:50%% 0}to{object-position:50%% 22%%}}
.row{display:flex;gap:40px;align-items:center}
.side{display:flex;flex-direction:column;gap:22px;width:430px}
.chip{display:flex;align-items:center;gap:16px;background:#fbf8ef;color:#13241f;font-size:40px;font-weight:700;padding:22px 28px;border-radius:26px;box-shadow:0 20px 50px rgba(0,0,0,.35)}
.chip b{display:inline-flex;width:54px;height:54px;border-radius:50%%;background:#0b5d45;color:#fff;align-items:center;justify-content:center;font-size:32px;flex:none}
.chip.gold{background:#e3a237}.chip.gold b{background:#13241f}
.stamp{position:absolute;right:120px;top:300px;background:#e3a237;color:#13241f;font-weight:800;font-size:56px;padding:26px 34px;border-radius:50%%;width:230px;height:230px;
 display:flex;align-items:center;justify-content:center;text-align:center;line-height:1;transform:rotate(12deg);box-shadow:0 24px 60px rgba(0,0,0,.45);animation:stamp .6s cubic-bezier(.3,1.6,.5,1) 1.2s both;z-index:4}
@keyframes stamp{from{opacity:0;transform:scale(2.4) rotate(-20deg)}to{opacity:1;transform:rotate(12deg)}}
.tablet{width:840px;border-radius:44px;background:#0b1512;padding:22px;box-shadow:0 50px 120px rgba(0,0,0,.55),0 0 0 3px rgba(247,207,106,.45);position:relative;animation:tab 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes tab{from{opacity:0;transform:translateY(240px) rotateX(30deg)}to{opacity:1;transform:rotateX(8deg)}}
.tablet img{width:100%%;display:block;border-radius:26px}
.hl{position:absolute;height:64px;background:rgba(255,214,0,.42);border-radius:10px;mix-blend-mode:multiply;width:0;animation:hl 1.2s ease-out 1.6s forwards}
@keyframes hl{to{width:var(--w)}}
.live{position:absolute;right:40px;top:-30px;box-shadow:0 10px 30px rgba(0,0,0,.4);background:#c0392b;color:#fff;font-weight:800;font-size:30px;padding:8px 18px;border-radius:12px;animation:blink 1s steps(2) infinite}
@keyframes blink{50%%{opacity:.4}}
.chips3{display:flex;gap:18px;margin-top:34px}
.card{width:760px;border-radius:40px;overflow:hidden;box-shadow:0 50px 120px rgba(0,0,0,.55);position:relative;animation:card 1s cubic-bezier(.2,.8,.2,1) both;background:#fff}
@keyframes card{from{opacity:0;transform:translateX(400px) rotate(8deg)}to{opacity:1;transform:rotate(-2deg)}}
.card img{width:100%%;display:block}
.tick{position:absolute;right:-30px;top:-40px;width:150px;height:150px;border-radius:50%%;background:#e3a237;color:#13241f;font-size:90px;font-weight:800;display:flex;align-items:center;justify-content:center;box-shadow:0 20px 50px rgba(0,0,0,.4);animation:pop .7s cubic-bezier(.3,1.6,.5,1) 2.6s both}
.example{position:absolute;left:24px;top:24px;background:rgba(19,36,31,.82);color:#fff;font-size:30px;font-weight:650;padding:8px 18px;border-radius:12px}
.verse{width:900px;background:#fbf8ef;color:#13241f;border-radius:44px;padding:56px 60px;box-shadow:0 50px 120px rgba(0,0,0,.5);position:relative}
.verse .ar{font-family:Hafs;direction:rtl;text-align:center;font-size:72px;line-height:1.9;color:#0b3d2e}
.verse .tr{font-size:40px;line-height:1.35;text-align:center;margin-top:26px;color:#22352f;font-weight:500}
.verse .ref{font-size:30px;text-align:center;margin-top:22px;color:#7a5a12;font-weight:650}
.big{font-size:230px;font-weight:800;line-height:.9;color:#f7cf6a;letter-spacing:-6px;text-shadow:0 10px 50px rgba(0,0,0,.35)}
.qrbox{background:#fff;border-radius:32px;padding:20px;box-shadow:0 30px 80px rgba(0,0,0,.45);margin-top:26px}
.qrbox img{width:290px;height:290px;display:block}
.url{display:inline-block;background:#e3a237;color:#132018;font-weight:780;font-size:46px;padding:18px 40px;border-radius:60px;margin-top:26px}
.sub{position:absolute;left:70px;right:70px;bottom:430px;z-index:5;display:flex;justify-content:center}
.sub span{background:rgba(2,20,14,.78);border:1px solid rgba(247,207,106,.35);color:#fff;font-size:40px;line-height:1.3;font-weight:560;text-align:center;padding:18px 28px;border-radius:22px;animation:sub .4s ease-out both}
.rtlx{font-family:N,serif;direction:rtl;unicode-bidi:isolate;letter-spacing:0;line-height:1.9}
h1 .rtlx{font-size:.72em;line-height:1.75}.chip .rtlx{line-height:1.7}.sub .rtlx{display:block;line-height:1.75;font-size:38px}
@keyframes sub{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
.prog{position:absolute;left:70px;right:70px;top:70px;height:6px;background:rgba(255,255,255,.14);border-radius:6px;overflow:hidden;z-index:6}
.prog i{display:block;height:100%%;background:#e3a237;animation:grow linear both}
@keyframes grow{from{width:var(--a)}to{width:var(--b)}}
""" % {"A": A, "HAFS": HAFS_FONT}

GOLD = ('<svg width="0" height="0" style="position:absolute"><defs><linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#fff3c4"/><stop offset=".45" stop-color="#e6b04c"/><stop offset="1" stop-color="#9c6516"/></linearGradient></defs></svg>')
TOP = f'<div class="top in">{LOGO}<div><b>Nurul Huda Academy</b><span>نور الہدیٰ اکیڈمی</span></div></div>'
ARCH = ('<svg class="frame" viewBox="0 0 620 760"><path d="M40 740 V330 C40 170 180 60 310 20 C440 60 580 170 580 330 V740 Z"/>'
        '<path class="in2" d="M78 740 V340 C78 200 200 104 310 62 C420 104 542 200 542 340 V740 Z"/></svg>')


def t(s):
    """Escape text but keep <em> and <br> (the only markup allowed in spec text)."""
    s = html.escape(s or "")
    s = re.sub(r"&lt;(/?em|br)&gt;", r"<\1>", s)
    if re.search(r"[\u0600-\u06FF]", s):     # Urdu / Arabic caption or headline: Nastaliq font, right to left
        s = f'<span class="rtlx" dir="rtl">{s}</span>'
    return s


def chips(items, start=2, gold=None):
    out = "".join(f'<div class="chip pop d{min(start+i,6)}"><b>✓</b>{t(c)}</div>' for i, c in enumerate(items))
    if gold:
        out += f'<div class="chip gold pop d{min(start+len(items),6)}"><b>★</b>{t(gold)}</div>'
    return out


def ur(s, d=4, style=""):
    return f'<div class="ur in d{d}" style="{style}">{t(s)}</div>' if s else ""


def body(sc):
    k = sc["kind"]
    kick = f'<div class="kicker in">{t(sc["kicker"])}</div>' if sc.get("kicker") else ""
    if k == "opener":          # logo drawn inside a gold arch, then the headline
        return (f'<div class="glow"></div><div class="stage"><div class="arch">{ARCH}<div class="lg">{LOGO}</div></div>'
                f'<h1 class="in d3" style="margin-top:-20px">{t(sc["h1"])}</h1>{ur(sc.get("ur"))}</div>')
    if k == "headline":        # a big statement, optional chips under it
        return (f'{TOP}<div class="glow"></div><div class="stage">{kick}<h1 class="in d1">{t(sc["h1"])}</h1>'
                f'<div class="side" style="width:760px;margin-top:50px">{chips(sc.get("chips", []), 2, sc.get("gold"))}</div>'
                f'{ur(sc.get("ur"), 5)}</div>')
    if k == "number":          # one large figure (only true figures: 30 minutes, 1 to 1, 8 languages...)
        return (f'{TOP}<div class="glow"></div><div class="stage">{kick}<div class="big pop d1">{t(sc["big"])}</div>'
                f'<h1 class="in d2" style="font-size:80px;margin-top:20px">{t(sc["h1"])}</h1>{ur(sc.get("ur"))}</div>')
    if k == "phone":           # a phone showing a screenshot that scrolls gently; optional chips beside it
        size = ' style="width:380px;height:780px"' if sc.get("chips") else ""
        img = f'<div class="phone"{size}><img src="{asset(sc["img"])}"></div>'
        stamp = f'<div class="stamp">{t(sc["stamp"])}</div>' if sc.get("stamp") else ""
        if sc.get("chips"):
            return (f'{TOP}<div class="stage">{kick}<div class="row">{img}<div class="side">{chips(sc["chips"])}'
                    f'{ur(sc.get("ur"), 5, "font-size:46px")}</div></div></div>')
        return f'{TOP}{stamp}<div class="stage">{kick}{img}{ur(sc.get("ur"))}</div>'
    if k == "board":           # the live lesson board on a tablet, with highlights sweeping over words
        hls = "".join(f'<div class="hl" style="left:{x}%;top:{y}%;--w:{w}%;animation-delay:{1.6+i}s"></div>'
                      for i, (x, y, w) in enumerate(sc.get("highlights", [[9, 47.5, 30], [58, 53.4, 33]])))
        tags = "".join(f'<div class="chip pop d{3+i}"><b>{t(a)}</b>{t(b)}</div>' for i, (a, b) in enumerate(sc.get("tags", [])))
        return (f'{TOP}<div class="stage">{kick}<div class="tablet"><div class="live">● LIVE</div><img src="{asset(sc.get("img", "board.jpg"))}">'
                f'{hls}</div><div class="chips3">{tags}</div></div>')
    if k == "card":            # a picture card sliding in (the class report, the dashboard)
        badge = f'<div class="example">{t(sc.get("badge", "Example"))}</div>' if sc.get("badge", "Example") else ""
        return (f'{TOP}<div class="glow"></div><div class="stage">{kick}<div class="card"><img src="{asset(sc["img"])}">'
                f'{badge}<div class="tick">✓</div></div>{ur(sc.get("ur"), 4, "margin-top:40px")}</div>')
    if k == "verse":           # Quran text from the King Fahd data, never typed; translation from a published source
        s, a = sc["ref"][0], sc["ref"][1]
        b = sc["ref"][2] if len(sc["ref"]) > 2 else a
        if not sc.get("translation"):
            sc["translation"], sc["translation_source"] = translation(s, a, b)
        if not sc.get("translation_source"):
            sys.exit("verse scene needs translation_source (a published translation, named)")
        return (f'{TOP}<div class="glow"></div><div class="stage">{kick}<div class="verse in d1"><div class="ar">{html.escape(ayat(s, a, b))}</div>'
                f'<div class="tr">{t(sc["translation"])}</div><div class="ref">Quran {s}:{a}{"–"+str(b) if b != a else ""} · '
                f'{t(sc["translation_source"])}</div></div></div>')
    if k == "end":             # call to action with the free-trial QR code
        qr = f'<div class="qrbox pop d3"><img src="{asset(sc.get("qr", "qr-free-trial.png"))}"></div>' if sc.get("qr", True) else ""
        return (f'<div class="glow"></div><div class="stage"><div class="lg pop" style="width:170px;height:170px">{LOGO}</div>'
                f'<h1 class="in d1" style="font-size:84px;margin-top:14px">{t(sc["h1"])}</h1>{ur(sc.get("ur"), 2)}'
                f'{qr}<div><span class="url in d4">{t(sc.get("url", "nurulhudaacademy.org"))}</span></div></div>')
    if k == "html":            # anything else: your own markup inside the stage, using the classes above
        return f'{TOP}<div class="stage">{sc["html"]}</div>'
    sys.exit(f"unknown scene kind: {k}")


def page(sc, start, end, total):
    return (f'<!doctype html><html><head><meta charset=utf-8><style>{CSS}</style></head><body>{GOLD}'
            f'<div class="rays"></div>{STAR}<div class="pts">{PARTICLES}</div>{body(sc)}'
            f'<div class="sub"><span>{t(sc["sub"])}</span></div>'
            f'<div class="prog"><i style="--a:{start/total*100:.2f}%;--b:{end/total*100:.2f}%;animation-duration:{end-start:.2f}s"></i></div>'
            f'</body></html>')


# ---------- timing ----------
def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def caption_time(sc):
    words = len(re.sub(r"<[^>]+>", " ", sc["sub"]).split())
    return sc.get("seconds") or max(3.4, 1.7 + 0.36 * words)


def voice_track(spec, work):
    """Greeting + narration as one file; returns (path, seconds before the narration starts) or (None, 0)."""
    v = spec.get("voice")
    if not v:
        return None, 0.0
    v = v if os.path.isabs(v) else os.path.join(os.path.dirname(spec["_path"]), v)
    out = os.path.join(work, "voice_full.wav")
    if spec.get("greeting", True):
        g = os.path.join(A, "greeting-assalamu-alaikum.mp3")
        lead = duration(g) + GAP_AFTER_GREETING
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", g, "-i", v, "-filter_complex",
                        f"[0:a]aresample=44100,aformat=channel_layouts=mono,apad=pad_dur={GAP_AFTER_GREETING}[g];"
                        "[1:a]aresample=44100,aformat=channel_layouts=mono[n];[g][n]concat=n=2:v=0:a=1[a]",
                        "-map", "[a]", out], check=True)
        return out, lead
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", v, "-ar", "44100", "-ac", "1", out], check=True)
    return out, 0.0


def syllables(text):
    """Rough speaking length of a caption: syllables, plus a little for commas and numbers."""
    x = re.sub(r"<[^>]+>", " ", text).lower().replace("nurulhudaacademy.org", "nurul huda academy dot org")
    n = sum(max(1, len(re.findall(r"[aeiouy]+", w))) for w in re.findall(r"[a-z0-9']+", x))
    return n + 1.5 * x.count(",") + 2 * len(re.findall(r"\d+", x))


def align(audio, subs, skip_before):
    """Scene boundaries at pauses in the voice, one sentence per scene. Working forward, each caption's length says
    roughly where its sentence ends (re-estimated from the last cut, so errors don't add up); the nearest pause wins,
    longer pauses preferred."""
    n = len(subs)
    r = subprocess.run(["ffmpeg", "-i", audio, "-af", "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    total = duration(audio)
    gaps = [((s + e) / 2, e - s) for s, e in zip(starts, ends) if s > skip_before + 0.4 and e < total - 0.2]
    if len(gaps) < n - 1:
        sys.exit(f"the voice has {len(gaps)} pauses but the spec has {n} scenes: one sentence per scene, please")
    w = [syllables(s) for s in subs]
    if skip_before:
        w[0] = max(2, w[0] - syllables("Assalamu alaikum"))      # the greeting is already counted in skip_before
    prev, speech_from, cuts = 0.0, skip_before, []
    for i in range(n - 1):
        expected = speech_from + (total - speech_from) * w[i] / sum(w[i:])
        left = n - 2 - i                                            # keep enough pauses for the scenes still to come
        cand = [g for g in gaps if g[0] > prev + 1.0][: max(1, len([g for g in gaps if g[0] > prev + 1.0]) - left)]
        mid, _ = min(cand, key=lambda g: abs(g[0] - expected) - 0.8 * min(g[1], 0.5))
        cuts.append(round(mid, 3)); prev = speech_from = mid
    print("scene cuts (s):", cuts)
    bounds = [0.0] + cuts + [round(total + TAIL, 3)]
    return list(zip(bounds[:-1], bounds[1:])), total


# ---------- Google Text-to-Speech: one clip per scene, so every cut lands exactly between sentences ----------
SCENE_GAP = 0.45       # silence between sentences


def google_key():
    """The key from GOOGLE_TTS_KEY, or from the website's settings table (Admin > Connections) via DATABASE_URL."""
    k = os.environ.get("GOOGLE_TTS_KEY", "").strip()
    if k:
        return k
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        try:
            import psycopg2
            with psycopg2.connect(url) as c, c.cursor() as cur:
                cur.execute("select value from settings where key = 'google_tts_key'")
                row = cur.fetchone()
                return row[0] if row else ""
        except Exception:
            return ""
    return ""


def google_say(key, text, tts, out):
    import base64, urllib.request, urllib.error
    body = {"input": {"text": text},
            "voice": {"languageCode": tts.get("lang", "en-GB"), **({"name": tts["voice"]} if tts.get("voice") else {})},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 44100, "speakingRate": tts.get("rate", 0.95)}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-Goog-Api-Key": key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            open(out, "wb").write(base64.b64decode(json.load(r)["audioContent"]))
    except urllib.error.HTTPError as e:
        sys.exit(f"Google Text-to-Speech refused ({e.code}): {e.read()[:300]!r}")


def list_voices(lang):
    """python3 reel.py --voices ur-IN : the Google voices for a language (pick a calm, clear female voice)."""
    import urllib.request
    key = google_key() or sys.exit("no Google key (GOOGLE_TTS_KEY, or Admin > Connections on the website)")
    req = urllib.request.Request(f"https://texttospeech.googleapis.com/v1/voices?languageCode={lang}", headers={"X-Goog-Api-Key": key})
    with urllib.request.urlopen(req, timeout=20) as r:
        for v in json.load(r).get("voices", []):
            print(v["name"], v["ssmlGender"], ",".join(v["languageCodes"]))


def google_timeline(spec, work):
    """Each scene's "say" (or its caption) spoken separately, then joined with short pauses: exact scene lengths."""
    key = google_key()
    if not key:
        return None
    tts = spec["tts"]
    parts, bounds, t = [], [0.0], 0.0
    g = os.path.join(A, "greeting-assalamu-alaikum.mp3")
    for i, sc in enumerate(spec["scenes"]):
        text = re.sub(r"<[^>]+>", " ", sc.get("say") or sc["sub"])
        text = re.sub(r"(?i)(www\.)?nurulhudaacademy\.org", "Nurul Huda Academy dot org", text)
        if i == 0 and spec.get("greeting", True):            # Dr Hayat's own greeting replaces the spoken one
            text = re.sub(r"^\s*assalamu?\s*alaikum[.,!]?\s*", "", text, flags=re.I)
        clip = os.path.join(work, f"say{i}.wav")
        google_say(key, text, tts, clip)
        parts.append((g, clip) if (i == 0 and spec.get("greeting", True)) else (clip,))
    seg_files = []
    for i, files in enumerate(parts):
        seg = os.path.join(work, f"seg{i}.wav")
        inputs = sum((["-i", f] for f in files), [])
        n = len(files)
        chain = "".join(f"[{j}:a]aresample=44100,aformat=channel_layouts=mono" + (f",apad=pad_dur={GAP_AFTER_GREETING}" if n == 2 and j == 0 else "") + f"[a{j}];" for j in range(n))
        chain += "".join(f"[a{j}]" for j in range(n)) + f"concat=n={n}:v=0:a=1,apad=pad_dur={SCENE_GAP}[o]"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", chain, "-map", "[o]", seg], check=True)
        seg_files.append(seg)
        t += duration(seg); bounds.append(round(t, 3))
    lst = os.path.join(work, "segs.txt")
    open(lst, "w").writelines(f"file '{f}'\n" for f in seg_files)
    out = os.path.join(work, "voice_full.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    bounds[-1] = round(bounds[-1] + TAIL, 3)
    print("Google voice, scene cuts (s):", bounds[1:-1])
    return list(zip(bounds[:-1], bounds[1:])), out


def timeline(spec, work):
    if spec.get("tts") and not spec.get("voice"):
        g = google_timeline(spec, work)
        if g:
            return g
        print("No Google key found: making this video caption-only.")
    audio, lead = voice_track(spec, work)
    n = len(spec["scenes"])
    if audio:
        if spec.get("cuts"):                                        # manual override: seconds where each new scene starts
            bounds = [0.0] + spec["cuts"] + [round(duration(audio) + TAIL, 3)]
            return list(zip(bounds[:-1], bounds[1:])), audio
        sc, _ = align(audio, [s["sub"] for s in spec["scenes"]], lead)
        return sc, audio
    out, t0 = [], 0.0
    for s in spec["scenes"]:
        d = caption_time(s)
        out.append((round(t0, 3), round(t0 + d, 3))); t0 += d
    return out, None


# ---------- drawing ----------
def render(i, sc, start, end, total, pg, work):
    dur = end - start
    p = os.path.join(work, f"scene{i}.html")
    open(p, "w").write(page(sc, start, end, total))
    pg.goto("file://" + p); pg.wait_for_timeout(500)
    pg.evaluate("document.fonts.ready")
    tmp, out = os.path.join(work, f"s{i}.tmp.mp4"), os.path.join(work, f"s{i}.mp4")
    fo = 0.35
    vf = (f"fade=in:st=0:d={fo}:color=0x021a13," if i else "") + f"fade=out:st={dur-fo:.3f}:d={fo}:color=0x021a13"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                           "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp],
                          stdin=subprocess.PIPE)
    for f in range(int(round(dur * FPS))):
        pg.evaluate(f"document.getAnimations().forEach(a=>{{a.pause();a.currentTime={f / FPS * 1000}}})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=90))
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit(f"ffmpeg failed on scene {i}")
    os.replace(tmp, out)
    return out


def preview(spec, work):
    scenes, _ = timeline(spec, work)
    total = scenes[-1][1]
    shots = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        for i, (sc, (s, e)) in enumerate(zip(spec["scenes"], scenes)):
            path = os.path.join(work, f"scene{i}.html")
            open(path, "w").write(page(sc, s, e, total))
            pg.goto("file://" + path); pg.wait_for_timeout(600)
            pg.evaluate("document.fonts.ready")
            pg.evaluate(f"document.getAnimations().forEach(a=>{{a.pause();a.currentTime={min(e - s - 0.5, 4.0) * 1000}}})")
            shot = os.path.join(work, f"preview{i}.png"); pg.screenshot(path=shot); shots.append(shot)
        b.close()
    print("\n".join(shots))


def build(spec, work, outdir):
    scenes, audio = timeline(spec, work)
    total = scenes[-1][1]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        files = [render(i, sc, s, e, total, pg, work) for i, (sc, (s, e)) in enumerate(zip(spec["scenes"], scenes))]
        b.close()
    lst = os.path.join(work, "list.txt")
    open(lst, "w").writelines(f"file '{f}'\n" for f in files)
    silent = os.path.join(work, "silent.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    whoosh = os.path.join(work, "whoosh.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anoisesrc=d=0.9:c=pink:a=0.5", "-af",
                    "highpass=f=300,lowpass=f=3500,afade=t=in:d=0.35,afade=t=out:st=0.4:d=0.5,volume=0.22", "-ar", "44100", whoosh], check=True)
    inputs, filt, mix, k = ["-i", silent], [], [], 1
    if audio:
        inputs += ["-i", audio]; filt.append(f"[{k}:a]aresample=44100[v]"); mix.append("[v]"); k += 1
    for j, (c, _) in enumerate(scenes[1:]):
        d = int(max(0, c - 0.45) * 1000)
        inputs += ["-i", whoosh]; filt.append(f"[{k}:a]adelay={d}|{d}[w{j}]"); mix.append(f"[w{j}]"); k += 1
    filt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,apad,atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5[a]")
    os.makedirs(outdir, exist_ok=True)
    full = os.path.join(outdir, f"{spec['slug']}.mp4")
    small = os.path.join(outdir, f"{spec['slug']}-720.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", full], check=True)
    # Small copy for Google Drive (its upload limit is about 3 MB per file through Claude).
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", full, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "27", "-maxrate", "520k", "-bufsize", "1040k", "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart", small], check=True)
    cover = os.path.join(outdir, f"{spec['slug']}-cover.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{scenes[0][1] - 0.6:.2f}", "-i", full, "-frames:v", "1", "-q:v", "3", cover], check=True)
    mb = os.path.getsize(small) / 1e6
    print(f"built {total:.1f}s  {'narrated' if audio else 'caption-only'}\n{full}\n{small} ({mb:.2f} MB)\n{cover}")
    if mb > 3.0:
        print("WARNING: the small copy is over 3 MB; shorten the video or raise -crf to 29")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--voices":
        list_voices(sys.argv[2] if len(sys.argv) > 2 else "en-GB"); sys.exit()
    spec_path = os.path.abspath(sys.argv[1])
    spec = json.load(open(spec_path)); spec["_path"] = spec_path
    work = os.path.join(os.path.dirname(spec_path), f".work-{spec['slug']}")
    os.makedirs(work, exist_ok=True)
    outdir = os.environ.get("REEL_OUT", os.path.join(os.path.dirname(spec_path), "out"))
    preview(spec, work) if "--preview" in sys.argv else build(spec, work, outdir)
