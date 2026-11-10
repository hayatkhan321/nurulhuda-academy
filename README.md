# Nurul Huda Academy

Public website for nurulhudaacademy.org: online Quran and Arabic classes for children.
Built in the same pattern as hayatclinics.com (Flask on Vercel, Supabase Postgres, e-mail through Resend).

## Pages
Home, Courses, For families, Book a free trial (form), Teach with us (form), Videos, About, Contact, Terms and privacy.
Sign-ups are listed at `/admin` (password from `ADMIN_PASSWORD`).

## Settings (Vercel environment variables)
| Name | What it is |
| --- | --- |
| `DATABASE_URL` | Supabase Postgres connection string. Without it, sign-ups are kept only briefly. |
| `SECRET_KEY` | Any long random text. |
| `ADMIN_PASSWORD` | Password for `/admin`. |
| `RESEND_API_KEY` | Resend key, so confirmation and notification e-mails are sent. |
| `MAIL_FROM` | Default `Nurul Huda Academy <hello@nurulhudaacademy.org>`; verify the domain in Resend first. |
| `NOTIFY_EMAIL` | Where new sign-ups are announced. Default nurulhudaacademy2@gmail.com. |
| `APP_ENV` | `production` on Vercel. |

## Adding a short video
Upload it to YouTube, then add `{"title": "...", "youtube": "VIDEO_ID"}` to `VIDEOS` in `nurulhuda/content.py`.

## Run locally
```
pip install -r requirements.txt
python app.py
```
