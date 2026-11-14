# Nurul Huda Academy

Public website for nurulhudaacademy.org: online Quran and Arabic classes for children.
Built in the same pattern as hayatclinics.com (Flask on Vercel, Supabase Postgres, e-mail through Resend).

## Pages
Home, Courses, For families, Book a free trial (form), Teach with us (form), Videos, About, Contact, Terms and privacy.
Sign-ups are listed at `/admin` (password from `ADMIN_PASSWORD`).

## Settings (Vercel environment variables)
| Name | What it is |
| --- | --- |
| `DATABASE_URL` | Supabase pooler address without the password: `postgresql://postgres.paqpdnpnhrkcvxyrwofi@aws-1-us-east-1.pooler.supabase.com:6543/postgres` |
| `DB_PASSWORD` | The Supabase database password on its own (symbols are fine). |
| `SECRET_KEY` | Any long random text. |
| `ADMIN_PASSWORD` | Password for `/admin`. |
| `RESEND_API_KEY` | Resend key, so confirmation and notification e-mails are sent. |
| `MAIL_FROM` | Default `Nurul Huda Academy <hello@nurulhudaacademy.org>`; verify the domain in Resend first. |
| `NOTIFY_EMAIL` | Where new sign-ups are announced. Default nurulhudaacademy2@gmail.com. |
| `CONTACT_EMAIL` / `ADMIN_EMAIL` | Public addresses, default info@ and admin@nurulhudaacademy.org (ImprovMX forwards both to the academy Gmail). |
| `APP_ENV` | `production` on Vercel. |

## Adding a short video
Upload it to YouTube, then add `{"title": "...", "youtube": "VIDEO_ID"}` to `VIDEOS` in `nurulhuda/content.py`.

## Run locally
```
pip install -r requirements.txt
python app.py
```

## Languages
The site shows in English, Urdu, Arabic, Hindi, Malay, Indonesian, Spanish and French. It picks the visitor's
language from their phone or browser, and anyone can switch with the globe button (the choice is remembered).
- English lines are numbered in `nurulhuda/i18n/keys.json`; each `<code>.json` holds the translations by number.
- After changing page text, run `python scripts/i18n_extract.py` to list lines that still need translating.
- Anything not yet translated simply shows in English. The admin area stays in English.
- Forms ask for first, second and third language with a level, plus English and Urdu levels (and Arabic for
  teachers). Admin > Teachers can filter by English and Urdu level.

## Books (audit-ready)
Admin > **Books** shows each month in AED, automatic health checks, month closing, and the audit pack download.
- Money records are append-only (enforced by database triggers): payments, refunds, payouts, expenses and the
  activity log can be added but never changed or deleted. Mistakes are corrected with a numbered entry.
- Numbers run per year with no gaps: RC- receipts, RF- refunds, CN- credit notes, PV- teacher payouts, EX- expenses.
- Every amount is stored with the AED rate of the day. Families get an e-mailed receipt and can print it from "My classes".
- Closing a month locks classes, decisions and expenses dated in it.
- Every action by founders, teachers and families is in the activity log.
- Claude (optional): set `ANTHROPIC_API_KEY` to switch on "Ask Claude about the books" and Claude's review in the
  monthly e-mail. Set `CRON_SECRET` so Vercel's monthly job (`vercel.json`) can send the review to admin@.
