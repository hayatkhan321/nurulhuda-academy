"""Build clear, text-based Quran PDFs with a translation under every verse.

Arabic: King Fahd Glorious Quran Printing Complex, Uthmanic Hafs data v18 with its own Uthmanic Hafs v18 font.
Urdu:   Muhammad Junagarhi (Tanzil.net text). Old presentation-form letters normalised to standard Unicode,
        and word-final Arabic heh (ه) after non-joining letters written as Urdu heh goal (ہ), as Urdu is printed.
Hindi:  Maulana Azizul Haq al-Umari (QuranEnc.com, King Fahd Complex translation), unchanged.
Fonts:  KFGQPC Uthmanic Hafs 18, Noto Nastaliq Urdu, Noto Sans Devanagari, Amiri (all free licences).
"""
import html, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
Q = json.load(open(ROOT / "data/hafsData_v18.json"))
F = (ROOT / "fonts").resolve()

LANGS = {
    "ur": {"file": "urd-muhammadjunagar", "dir": "rtl", "font": "NotoNastaliqUrdu", "size": "14.5pt", "lh": "2.15",
           "title": "قرآن مجید", "subtitle": "مع اردو ترجمہ", "translator": "مولانا محمد جوناگڑھی",
           "translator_en": "Muhammad Junagarhi", "lang_en": "Urdu",
           "source": "Urdu translation text: Tanzil.net (tanzil.net/trans), shown without change except standard "
                     "Unicode spelling in place of old presentation forms.",
           "surah": "سورۃ", "ayat": "آیات", "juz": "پارہ", "contents": "فہرست سورتیں"},
    "hi": {"file": "hin-maulanaazizulha", "dir": "ltr", "font": "NotoSansDevanagari", "size": "12pt", "lh": "1.7",
           "title": "क़ुरआन मजीद", "subtitle": "हिन्दी अनुवाद के साथ", "translator": "मौलाना अज़ीज़ुल हक़ उमरी",
           "translator_en": "Maulana Azizul Haq al-Umari", "lang_en": "Hindi",
           "source": "Hindi translation: QuranEnc.com (The Noble Quran Encyclopedia), translation by Maulana Azizul Haq "
                     "al-Umari published by the King Fahd Complex, shown without change except footnote numbers, as the notes are not included.",
           "surah": "सूरह", "ayat": "आयतें", "juz": "पारा", "contents": "सूरतों की सूची"},
}
BISMILLAH = Q[0]["aya_text"].split("\xa0")[0]


def urdu_clean(s: str) -> str:
    out = []
    for ch in s:
        cp = ord(ch)
        if ch in "﴾﴿":
            out.append("(" if ch == "﴿" else ")")   # ornate brackets: RTL text shows them mirrored
        elif 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            out.append(unicodedata.normalize("NFKC", ch))
        else:
            out.append(ch)
    s = "".join(out)
    # Word-final Arabic heh (after a letter, before a space, punctuation or the end) is written as Urdu heh goal.
    letters = "ء-يٮ-ۓ"
    s = re.sub(f"(?<=[{letters}])ه(?![{letters}])", "ہ", s)
    # ...and after a letter that does not join forward (ا د ذ ر ز و ڈ ڑ ژ), as in گناہگار
    return re.sub("(?<=[ادذرزوڈڑژ])ه", "ہ", s)


def build(code: str) -> str:
    L = LANGS[code]
    tr = json.load(open(ROOT / f"data/{L['file']}.json"))["quran"]
    # The Hindi text carries footnote markers like [1] whose notes are not in the source data: leave them out.
    texts = [urdu_clean(v["text"]) if code == "ur" else re.sub(r"\s*\[\d+\]", "", v["text"]) for v in tr]
    surahs = {}
    for a in Q:
        surahs.setdefault(a["sora"], {"en": a["sora_name_en"], "ar": a["sora_name_ar"], "n": 0})["n"] += 1
    e = html.escape
    parts = [f"""<!doctype html><html><head><meta charset="utf-8"><title>{e(L['title'])} {e(L['subtitle'])}</title><style>
@font-face {{ font-family: Hafs; src: url('file://{F}/hafs.18.ttf'); }}
@font-face {{ font-family: Tr; src: url('file://{F}/{L['font']}.ttf'); }}
@font-face {{ font-family: Amiri; src: url('file://{F}/Amiri-Regular.ttf'); }}
@font-face {{ font-family: Amiri; font-weight: 700; src: url('file://{F}/Amiri-Bold.ttf'); }}
@page {{ size: A4; margin: 16mm 15mm 18mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #111; font-family: Tr, Amiri, serif; }}
.cover {{ height: 255mm; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
  border: 3px double #0b5d45; padding: 20mm; page-break-after: always; }}
.cover .t {{ font-family: Hafs; font-size: 54pt; color: #0b5d45; margin: 0; line-height: 1.6; }}
.cover .s {{ font-size: 24pt; margin: 6mm 0; direction: {L['dir']}; }}
.cover .by {{ font-size: 16pt; direction: {L['dir']}; }}
.cover .meta {{ font-family: Amiri; font-size: 10.5pt; color: #444; margin-top: 18mm; line-height: 1.6; direction: ltr; }}
.toc {{ page-break-after: always; }}
.toc h1 {{ text-align: center; color: #0b5d45; font-size: 20pt; font-weight: 400; direction: {L['dir']}; }}
.toc ol {{ columns: 3; column-gap: 8mm; list-style: none; padding: 0; margin: 0; font-family: Amiri; font-size: 11pt; direction: ltr; }}
.toc li {{ break-inside: avoid; padding: 1.2mm 0; border-bottom: 1px dotted #ccc; }}
.toc a {{ color: #111; text-decoration: none; display: flex; justify-content: space-between; gap: 2mm; }}
.toc .ar {{ font-family: Hafs; font-size: 14pt; line-height: 1; }}
.surah {{ break-before: page; }}
.surah:first-of-type {{ break-before: auto; }}
.head {{ border: 2px solid #0b5d45; border-radius: 3mm; padding: 2mm 5mm; margin: 0 0 3mm; display: flex; align-items: center;
  justify-content: space-between; background: #f1f8f4; font-family: Amiri; font-size: 10.5pt; color: #0b5d45; }}
.head h2 {{ font-family: Hafs; font-weight: 400; font-size: 24pt; margin: 0; color: #073d2e; line-height: 1.5; }}
.bism {{ font-family: Hafs; font-size: 24pt; text-align: center; margin: 1mm 0 3mm; line-height: 1.8; }}
.juz {{ font-family: Amiri; text-align: center; color: #9c6516; font-size: 10.5pt; margin: 2mm 0; border-top: 1px solid #e3cf9f;
  border-bottom: 1px solid #e3cf9f; padding: 0.5mm 0; direction: {L['dir']}; }}
.v {{ padding: 2.2mm 0 2.4mm; border-bottom: 1px solid #e6ece9; }}
.v .ar {{ break-inside: avoid; break-after: avoid; }}
.tr {{ orphans: 2; widows: 2; }}
.head, .bism, .juz {{ break-after: avoid; }}
.ar {{ font-family: Hafs; font-size: 20pt; line-height: 2.0; direction: rtl; text-align: right; }}
.tr {{ font-family: Tr; font-size: {L['size']}; line-height: {L['lh']}; direction: {L['dir']}; text-align: start; color: #1c2a25; }}
.tr .n {{ font-family: Amiri; color: #0b5d45; font-size: 10pt; margin-inline-end: 1.5mm; }}
</style></head><body>
<section class="cover">
  <p class="t">ٱلۡقُرۡءَانُ ٱلۡكَرِيمُ</p>
  <p class="s">{e(L['title'])}<br>{e(L['subtitle'])}</p>
  <p class="by">{e(L['translator'])}</p>
  <div class="meta">The Noble Quran with {L['lang_en']} translation by {e(L['translator_en'])}<br>
  Arabic text: King Fahd Glorious Quran Printing Complex, Madinah (Uthmanic Hafs, version 18), with the Complex's own Uthmanic Hafs font.<br>
  {e(L['source'])}<br>Prepared for free teaching by Nurul Huda Academy, nurulhudaacademy.org, 2026. Not for sale.</div>
</section>
<section class="toc"><h1>{e(L['contents'])}</h1><ol>"""]
    for n, s in surahs.items():
        parts.append(f'<li><a href="#s{n}"><span>{n}. {e(s["en"])}</span><span class="ar">{e(s["ar"])}</span></a></li>')
    parts.append("</ol></section>")
    last_juz, cur = 0, 0
    for a, t in zip(Q, texts):
        n = a["sora"]
        if n != cur:
            if cur:
                parts.append("</section>")
            cur, s = n, surahs[n]
            parts.append(f'<section class="surah" id="s{n}"><h1 style="font-size:0;margin:0">{n}. {e(s["en"])}</h1>'
                         f'<div class="head"><span>{L["surah"]} {n} · {e(s["en"])}</span><h2>سُورَةُ {e(s["ar"])}</h2>'
                         f'<span>{s["n"]} {L["ayat"]}</span></div>')
            if n not in (1, 9):
                parts.append(f'<div class="bism">{BISMILLAH}</div>')
        if a["jozz"] != last_juz:
            last_juz = a["jozz"]
            parts.append(f'<div class="juz">{L["juz"]} {last_juz} · Juz {last_juz}</div>')
        parts.append(f'<div class="v"><div class="ar">{e(a["aya_text"])}</div>'
                     f'<div class="tr"><span class="n">{n}:{a["aya_no"]}</span>{e(t)}</div></div>')
    parts.append("</section></body></html>")
    return "".join(parts)


if __name__ == "__main__":
    for code in sys.argv[1:] or LANGS:
        (ROOT / f"out/quran-{code}.html").write_text(build(code), encoding="utf-8")
        print("wrote", code)
