#!/usr/bin/env python3
"""Count a word root in the Quran, with the method written down, for "Quran facts" videos.

    python3 qcount.py رحم                 # every word built on the root ر ح م
    python3 qcount.py رحم --lemma رَحْمَة   # only one word (lemma) of that root
    python3 qcount.py رحم --json out.json  # also save the result for the captions Doc

Never put a count in a video that was not produced by this script, and always show the method line with it.

Sources
- Roots and lemmas: the Quranic Arabic Corpus morphology (Kais Dukes, corpus.quran.com, GNU GPL), in the plain-text
  copy at github.com/mustafa0x/quran-morphology. It is downloaded to data/ on first use (not committed).
- Cross-check: every counted word is looked up in the verified King Fahd Complex text (public/quran/hafs-v18.json,
  the same text the verse scene uses): its verse must exist and contain a word with the root letters in order.

What is counted: each word of the Quran (as the corpus divides words) that has a segment with that root, counted
once, across all 6,236 verses. The basmala is counted only where it is a verse (Al-Fatihah 1:1), as in the mushaf.
Different counting methods (exact spelling only, or including related roots) give different numbers, which is why
the method goes on screen. A count must be approved by the Head of Academics before a video is posted.
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HAFS_DATA = os.path.join(REPO, "public", "quran", "hafs-v18.json")
MORPH_URL = "https://raw.githubusercontent.com/mustafa0x/quran-morphology/master/quran-morphology.txt"
MORPH = os.path.join(HERE, "data", "quran-morphology.txt")

# Buckwalter-free: roots in the corpus file are written in Arabic letters, e.g. رحم
HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿ ]")
NORM = str.maketrans({"ٱ": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": ""})


def plain(s):
    return HARAKAT.sub("", s).translate(NORM)


def load_morph():
    if not os.path.exists(MORPH):
        os.makedirs(os.path.dirname(MORPH), exist_ok=True)
        print(f"downloading the corpus morphology from {MORPH_URL}", file=sys.stderr)
        urllib.request.urlretrieve(MORPH_URL, MORPH)
    words = {}  # (s, a, w) -> list of (form, tags)
    for line in open(MORPH, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4 or not parts[0][0].isdigit():
            continue
        s, a, w, _seg = map(int, parts[0].split(":"))
        words.setdefault((s, a, w), []).append((parts[1], parts[3]))
    return words


def tag(tags, key):
    for t in tags.split("|"):
        if t.startswith(key + ":"):
            return t[len(key) + 1:]
    return None


def count(root, lemma=None):
    words = load_morph()
    hafs = {(s, a): t for page in json.load(open(HAFS_DATA, encoding="utf-8"))["pages"] for s, a, t in page}
    hits, lemmas, unchecked = [], Counter(), []
    for (s, a, w), segs in sorted(words.items()):
        seg_roots = [(tag(t, "ROOT"), tag(t, "LEM")) for _f, t in segs]
        match = [(r, l) for r, l in seg_roots if r == root and (lemma is None or plain(l or "") == plain(lemma))]
        if not match:
            continue
        form = "".join(f for f, _t in segs)
        hits.append({"ref": f"{s}:{a}:{w}", "form": form, "lemma": match[0][1]})
        lemmas[match[0][1]] += 1
        verse = hafs.get((s, a))
        # cross-check: the verified verse exists and has a word containing the root letters in order
        pat = ".*".join(map(re.escape, plain(root)))
        if verse is None or not any(re.search(pat, plain(x)) for x in verse.split()):
            unchecked.append(f"{s}:{a}:{w}")
    verses = sorted({tuple(map(int, h["ref"].split(":")[:2])) for h in hits})
    method = (f"Every word built on the root {' '.join(root)} counted once, across the whole Quran "
              f"(Quranic Arabic Corpus morphology, cross-checked against the King Fahd Complex text)"
              + (f"; only the word {lemma}" if lemma else "") + ".")
    return {"root": root, "lemma": lemma, "words": len(hits), "verses": len(verses),
            "surahs": len({s for s, _a in verses}), "lemmas": lemmas.most_common(),
            "first": hits[:5], "not_cross_checked": unchecked, "method": method,
            "sources": ["Quranic Arabic Corpus morphology (corpus.quran.com), via github.com/mustafa0x/quran-morphology",
                        "King Fahd Glorious Quran Printing Complex, Uthmanic Hafs v18 (public/quran/hafs-v18.json)"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="root in Arabic letters without spaces, e.g. رحم")
    ap.add_argument("--lemma", help="count only this lemma (word) of the root")
    ap.add_argument("--json", help="also write the result to this file")
    args = ap.parse_args()
    r = count(args.root, args.lemma)
    print(f"root {args.root}: {r['words']} words in {r['verses']} verses of {r['surahs']} surahs")
    for l, n in r["lemmas"]:
        print(f"  {n:4d}  {l}")
    print("first:", ", ".join(f"{h['ref']} {h['form']}" for h in r["first"]))
    print("not cross-checked:", len(r["not_cross_checked"]), r["not_cross_checked"][:10])
    print("method:", r["method"])
    if args.json:
        json.dump(r, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
