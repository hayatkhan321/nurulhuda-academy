# Nurul Huda Academy short videos

`reel.py` makes vertical videos (1080x1920, 30 fps) for Instagram Reels, YouTube Shorts, TikTok, Facebook and
WhatsApp Status, in the academy's look: deep green, gold Islamic pattern, the logo, English and Urdu text, and a
caption on every scene so the video works with the sound off.

```
pip install playwright --break-system-packages   # only if missing; Chromium must already be installed
python3 reel.py specs/my-video.json --preview     # one still per scene: look at them before building
python3 reel.py specs/my-video.json               # builds out/<slug>.mp4, out/<slug>-720.mp4 (for Drive), out/<slug>-cover.jpg
```

## Rules (from Dr Hayat; these are not optional)

1. **No Quran recitation by AI or text-to-speech, ever.** The narrator speaks English (or Urdu) only.
2. **Quranic Arabic only from the verified King Fahd Complex text**, through a `verse` scene (it reads
   `public/quran/hafs-v18.json` and draws it in the Hafs font). Never type, paste or generate Arabic verses.
   Translations only from a named published translation (the verse scene fetches Sahih International by default).
3. **No hadith** in videos for now (the hadith page is still waiting for a scholar's check).
4. **No music.** The only sounds are the narration, Dr Hayat's recorded "Assalamu alaikum", and soft whooshes.
5. **No AI-generated faces of children** (or of anyone). Use the app screenshots in `assets/`, the logo, and text.
6. **Never post anything.** Videos go to Google Drive for Dr Hayat's weekly approval.
7. **Only true claims.** Use facts from the website or the week's marketing pack: free trial class, one to one,
   live, 30 minutes, tested teachers, female teachers on request, Head of Academics is a Hafiza, a report after
   every class, pay only for classes that take place. No invented numbers, reviews, testimonials or rankings.
8. No donations, no fatwas, no politics. Prices only as "see our Prices page".

## Voice

- Narrator: **Alice** (ElevenLabs, voiceId `Xb7hH8MSUJpSbSDYk0k2`), made with vidIQ `vidiq_voiceover_generate`.
  vidIQ is used **only** to make the voice file; never connect, upload or post through it (it is tied to the
  Hayat Clinics channel).
- Write the narration **without** "Assalamu alaikum": with `"greeting": true` the video opens with Dr Hayat's own
  recording (`assets/greeting-assalamu-alaikum.mp3`), then Alice. The first scene's caption still starts
  "Assalamu alaikum."
- **One sentence per scene**, in the same order as the scenes, and each scene's `sub` is that sentence. The tool
  finds the pauses between sentences and cuts there; it prints the cuts. If a cut looks wrong, set `"cuts"` in the
  spec (the seconds where scenes 2, 3, ... start).
- Credits: about 28 per 1000 characters, 150 a month on the free plan. One narrated video a week (under 450
  characters) fits; the others are caption-only (`"voice": null`).
- If the voice file cannot be downloaded (the workspace may block assets.vidiq.com), make the video caption-only
  and say so in the report.

## A spec

```json
{
  "slug": "female-teachers",
  "greeting": true,
  "voice": "narration.mp3",
  "scenes": [
    {"kind": "opener", "h1": "Want a <em>female</em> Quran teacher?", "ur": "...", "sub": "Assalamu alaikum. Want a female Quran teacher for your daughter?"},
    {"kind": "end", "h1": "Your first class is <em>free</em>", "ur": "پہلی کلاس مفت ہے", "sub": "Book a free trial class at nurulhudaacademy.org"}
  ]
}
```

Text may use `<em>` (gold words) and `<br>`. Keep headlines to about 8 words and captions to one sentence.
Urdu lines (`ur`) are optional; only write Urdu you are sure is correct and natural.

| kind | what it shows | fields |
|---|---|---|
| `opener` | gold arch drawing itself, logo, headline | `h1`, `ur` |
| `headline` | big statement with ticked chips | `kicker`, `h1`, `chips` [..], `gold` (one starred chip), `ur` |
| `number` | one large true figure | `kicker`, `big`, `h1`, `ur` |
| `phone` | a phone showing a screenshot, gently scrolling | `kicker`, `img`, `stamp` (badge), or `chips` beside it |
| `board` | the live lesson board on a tablet with highlights | `kicker`, `tags` [["1","One to one"], ...], `highlights` |
| `card` | a picture card sliding in (report, dashboard) | `kicker`, `img`, `ur` |
| `verse` | a Quran verse from the verified text + translation | `kicker`, `ref` [surah, ayah] or [surah, from, to] |
| `end` | logo, headline, free-trial QR code, website | `h1`, `ur`, `qr` (false to hide), `url` |
| `html` | your own markup inside the stage | `html` |

Every scene also needs `sub`; caption-only scenes may set `seconds`.

Images in `assets/`: `phone-home.jpg`, `phone-trial.jpg` (website on a phone), `board.jpg` (lesson board),
`report.jpg` (class report), `dashboard.jpg` (family dashboard), `qr-free-trial.png`. New screenshots of the live
website can be taken with Playwright at 390x844 and added here.

`specs/how-it-works.json` is the first video (v3); `specs/example-verse.json` shows the verse and number scenes.
