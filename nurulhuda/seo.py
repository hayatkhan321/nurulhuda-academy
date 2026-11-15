"""Search engine details for every public page: title, description, languages offered, structured data.

Titles and descriptions are written in English here and translated like the rest of the site (i18n/keys.json),
so each language version of a page has its own title and description in that language.
"""
from flask import current_app, request, url_for

from nurulhuda.i18n import LANGS

BRAND = "Nurul Huda Academy"

# endpoint -> (title without the brand, description). Keep titles under ~45 characters, descriptions under ~155.
META = {
    "site.home": ("Online Quran Classes for Kids, One to One",
                  "Live one-to-one Quran, Noorani Qaida, tajweed and hifz classes for children with tested teachers. "
                  "Female teachers on request. Book a free trial class."),
    "site.courses": ("Quran Courses for Kids: Qaida, Tajweed and Hifz",
                     "From Noorani Qaida to fluent reading, tajweed and hifz, plus Arabic and Islamic studies. "
                     "One-to-one online classes for children aged 4 and up."),
    "site.families": ("How Our Online Quran Classes Work",
                      "A free trial, the same tested teacher each week, a short report after every class, "
                      "and you pay only for classes that take place."),
    "site.pricing": ("Online Quran Class Prices and Family Discounts",
                     "Prices for one-to-one online Quran, tajweed, hifz and Arabic classes. Free trial class, family "
                     "discounts for siblings, and savings for paying upfront."),
    "site.trial": ("Book a free trial class",
                   "Book a free one-to-one trial Quran class for your child. Tell us their level and the times that "
                   "suit you, and we reply within one working day."),
    "site.teach": ("Teach Quran Online: Jobs for Quran Teachers",
                   "Teach Quran, tajweed and hifz online from home. We welcome qualified male and female teachers, "
                   "provide the classroom and pay for every class you teach."),
    "site.about": ("About Nurul Huda Academy",
                   "An online Quran academy for children, led by a Hafiza as Head of Academics, with tested teachers "
                   "and families around the world."),
    "site.videos": ("Short Videos About Learning the Quran",
                    "Short videos for parents and children about learning the Quran and how our online classes work."),
    "site.contact": ("Contact Us",
                     "Questions about classes, prices or teachers? Write to us and we reply within one working day."),
    "site.terms": ("Terms and Privacy",
                   "Our terms for classes, payments, cancellations and refunds, and how we look after your family's "
                   "personal information."),
    "site.vision": ("Our Vision: Jamia Nurul Huda",
                    "Our vision: world-class Islamic education that joins Deen and Dunya, grounded in knowledge, open to "
                    "all, and growing into Jamia Nurul Huda, an online university."),
    "site.islam": ("Discover Islam: Free Private Classes",
                   "Discover Islam: clear, friendly answers about what Muslims believe, and free private classes with a "
                   "teacher for anyone who is curious, considering Islam, or new to Islam."),
    "site.app": ("Get the Nurul Huda Academy App",
                 "Install the Nurul Huda Academy app on Android, iPhone, iPad and Windows. Free, small, and always up to date."),
    "site.resources": ("Free Quran PDFs, Noorani Qaida and Tajweed",
                       "Free resources for students and teachers: the Quran with translation, the Quran by juz (para) in "
                       "IndoPak and Madinah script, Noorani Qaida, tajweed and daily duas."),
    "site.why_quran": ("Why We Learn the Quran: Verses and Hadith",
                       "Why Muslims learn and recite the Quran: verses and authentic hadith on its reward, for children, "
                       "parents and families, with references."),
    "site.dashboard_demo": ("Family Dashboard Demo",
                            "See the family dashboard: classes left, weekly and monthly use, attendance, and each child's "
                            "progress in the Quran, updated after every class."),
}

# Pages not yet fully translated: only these languages are offered to search engines.
# (The hadith page waits for a scholar's check before translation; the demo is mostly sample numbers.)
PAGE_LANGS = {
    "site.why_quran": ["en"],
    "site.dashboard_demo": ["en"],
}

# Pages search engines should not list.
NOINDEX_PREFIXES = ("/admin", "/thanks", "/my", "/teacher", "/class", "/login", "/followups", "/board", "/offline", "/cron", "/whatsapp")

OG_LOCALE = {"en": "en_GB", "ur": "ur_PK", "ar": "ar_AE", "hi": "hi_IN", "ms": "ms_MY", "id": "id_ID", "es": "es_ES", "fr": "fr_FR"}


def langs_for(endpoint: str | None) -> list[str]:
    from nurulhuda import landing
    if endpoint in PAGE_LANGS:
        return PAGE_LANGS[endpoint]
    if endpoint == "site.landing":
        page = landing.PAGES.get((request.view_args or {}).get("slug"))
        return page["langs"] if page else ["en"]
    return list(LANGS)


def page_url(path: str, code: str) -> str:
    base = current_app.config["SITE_URL"].rstrip("/")
    return f"{base}{path}" + ("" if code == "en" else f"?lang={code}")


def context(lang: str) -> dict:
    """What base.html needs for the <head>."""
    endpoint = request.endpoint
    langs = langs_for(endpoint)
    offered = lang in langs
    title = desc = None
    if endpoint == "site.landing":
        from nurulhuda import landing
        page = landing.PAGES.get((request.view_args or {}).get("slug"))
        if page:
            text = landing.text(page, lang if offered else "en")
            title, desc = text["title"], text["desc"]
    elif endpoint in META:
        title, desc = META[endpoint]
    noindex = (not offered) or request.path.startswith(NOINDEX_PREFIXES)
    return {
        "seo_title": title,
        "seo_desc": desc,
        "seo_langs": langs,
        "seo_canonical": page_url(request.path, lang if offered else "en"),
        "seo_noindex": noindex,
        "seo_alternates": [(code, page_url(request.path, code)) for code in langs],
        "seo_og_locale": OG_LOCALE.get(lang if offered else "en", "en_GB"),
        "seo_image": current_app.config["SITE_URL"].rstrip("/") + url_for("static", filename="img/og-image.jpg"),
    }


def organization() -> dict:
    base = current_app.config["SITE_URL"].rstrip("/")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "EducationalOrganization",
                "@id": f"{base}/#org",
                "name": BRAND,
                "alternateName": "نور الهدى",
                "url": base,
                "logo": base + url_for("static", filename="icons/icon-512.png"),
                "email": current_app.config["CONTACT_EMAIL"],
                **({"telephone": "+" + current_app.config["WHATSAPP_PUBLIC_NUMBER"]}
                   if current_app.config.get("WHATSAPP_PUBLIC_NUMBER") else {}),
                "description": "Live one-to-one online Quran, Noorani Qaida, tajweed, hifz, Arabic and Islamic studies "
                               "classes for children, with tested teachers.",
                "areaServed": ["AE", "QA", "SA", "CA", "US", "GB", "PK", "IN", "MY", "ID"],
                "knowsLanguage": ["en", "ur", "ar", "hi", "ms", "id", "es", "fr"],
            },
            {
                "@type": "WebSite",
                "@id": f"{base}/#website",
                "url": base,
                "name": BRAND,
                "publisher": {"@id": f"{base}/#org"},
                "inLanguage": ["en", "ur", "ar", "hi", "ms", "id", "es", "fr"],
            },
        ],
    }


def courses_schema(path_steps, alongside) -> dict:
    """An ItemList of Course items for the Courses page (Google's course list rich result)."""
    base = current_app.config["SITE_URL"].rstrip("/")
    items = []
    for i, c in enumerate(list(path_steps) + list(alongside), start=1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Course",
                "url": f"{base}/courses#{c.get('key', c['name'].lower().replace(' ', '-'))}",
                "name": f"{c['name']} (online, one to one)",
                "description": c["text"],
                "provider": {"@type": "EducationalOrganization", "name": BRAND, "sameAs": base},
                "inLanguage": ["ar", "en", "ur"],
            },
        })
    return {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": items}
