# Urdu and Hindi Quran PDFs

Builds `public/quran/quran-urdu-junagarhi.pdf` and `public/quran/quran-hindi-umari.pdf`: every verse in the
Madinah script with the translation underneath, as real text (sharp at any zoom).

Sources (put them in `data/` and `fonts/` next to the scripts):
- Arabic: King Fahd Glorious Quran Printing Complex, Uthmanic Hafs data v18 (`hafsData_v18.json`) and font
  (`hafs.18.ttf`), from https://qurancomplex.gov.sa/en/techquran/dev/ (mirror: github.com/thetruetruth/quran-data-kfgqpc).
- Urdu: Muhammad Junagarhi, Tanzil.net text (`urd-muhammadjunagar.json` from github.com/fawazahmed0/quran-api).
- Hindi: Azizul Haq al-Umari, QuranEnc.com (`hin-maulanaazizulha.json`, same source).
- Fonts: Noto Nastaliq Urdu, Noto Sans Devanagari, Amiri (Google Fonts, OFL).

Run `python3 build.py && python3 render.py ur && python3 render.py hi` (needs Playwright with Chromium).
`public/quran/hafs-v18.json` (the lesson board's pages) is made from the same Hafs data.
