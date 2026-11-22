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

**Google voices (preferred, paid from the academy's Google Cloud credits).** Add to the spec:

```json
"tts": {"lang": "en-GB", "voice": "<a voice name>", "rate": 0.95}, "greeting": true, "voice": null
```

- Each scene's sentence (`say`, or its caption `sub`) is spoken separately and joined with short pauses, so every
  scene cut lands exactly between sentences. Use `say` when the spoken words should differ from the caption.
- With `"greeting": true` the video opens with Dr Hayat's own recording (`assets/greeting-assalamu-alaikum.mp3`); a
  leading "Assalamu alaikum" in the first sentence is dropped automatically so it isn't said twice.
- The key: `GOOGLE_TTS_KEY` in the environment. A scheduled run reads it from the website's database with the
  Supabase tool (`select value from settings where key = 'google_tts_key'`, project paqpdnpnhrkcvxyrwofi) and exports
  it for this command only. Never print it, write it to a file, commit it or put it in a report.
- Pick voices once with `python3 reel.py --voices en-GB` (then `ur-IN`, `ar-XA`): a calm, clear female voice in each
  language; prefer Chirp3-HD, Neural2 or WaveNet voices. Write the chosen names in this README.
- **Chosen voices (22 Nov 2026, calm female; Dr Hayat to approve):** en-GB `en-GB-Chirp3-HD-Aoede`,
  ur-IN `ur-IN-Chirp3-HD-Aoede`, ar-XA `ar-XA-Chirp3-HD-Aoede`, hi-IN `hi-IN-Chirp3-HD-Aoede`,
  id-ID `id-ID-Chirp3-HD-Aoede`, es-ES `es-ES-Chirp3-HD-Aoede`, fr-FR `fr-FR-Chirp3-HD-Aoede`,
  ms-MY `ms-MY-Wavenet-A` (Malay has no Chirp3-HD voice). These are the website's 8 languages.
- The workspace must be allowed to reach texttospeech.googleapis.com (claude.ai Settings > Capabilities). If it can't,
  or there is no key, the video is made caption-only and the report says so.
- Languages: English for every video; Urdu (`ur-IN`) and Arabic (`ar-XA`) versions use the same scenes with
  translated captions. Only write Urdu or Arabic you are sure is correct; mark them "to check" in the captions Doc.

**vidIQ (fallback only):** voice Alice (voiceId `Xb7hH8MSUJpSbSDYk0k2`) via `vidiq_voiceover_generate`, set as
`"voice": "narration.mp3"`. Use vidIQ only to make the voice file, never to connect, upload or post (it is tied to the
Hayat Clinics channel). About 28 credits per 1000 characters, 150 a month. With a vidIQ file, scene cuts come from
pauses in the voice (one sentence per scene); if a cut is wrong, set `"cuts"`.

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
| `card` | a picture card sliding in (report, dashboard), labelled "Example" because the screenshots are demo data | `kicker`, `img`, `ur`, `badge` |
| `verse` | a Quran verse from the verified text + translation | `kicker`, `ref` [surah, ayah] or [surah, from, to] |
| `end` | logo, headline, free-trial QR code, website | `h1`, `ur`, `qr` (false to hide), `url` |
| `html` | your own markup inside the stage | `html` |

Every scene also needs `sub`; caption-only scenes may set `seconds`.

Images in `assets/`: `phone-home.jpg`, `phone-trial.jpg` (website on a phone), `board.jpg` (lesson board),
`report.jpg` (class report), `dashboard.jpg` (family dashboard), `qr-free-trial.png`. New screenshots of the live
website can be taken with Playwright at 390x844 and added here.

`specs/how-it-works.json` is the first video (v3); `specs/example-verse.json` shows the verse and number scenes.
