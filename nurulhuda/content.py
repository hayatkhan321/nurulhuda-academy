"""Site copy that changes often lives here, like site_content.py on hayatclinics.com."""

BRAND = "Nurul Huda Academy"
BRAND_AR = "نور الهدى"

YOUTUBE = ""   # e.g. "https://www.youtube.com/@NurulHudaAcademy" once the channel exists
TIKTOK = ""
X_URL = ""
INSTAGRAM = ""

# The learning path. It really is a sequence, so the site numbers it.
PATH = [
    {"key": "qaida", "name": "Noorani Qaida", "ar": "القاعدة النورانية", "age": "Ages 4 and up",
     "text": "Arabic letters, their shapes and sounds, then joining them into words. The foundation for reading the Quran."},
    {"key": "nazira", "name": "Nazira", "ar": "الناظرة", "age": "After Qaida",
     "text": "Reading the Quran from the mushaf fluently and correctly, a few lines at a time, with daily revision."},
    {"key": "tajweed", "name": "Tajweed", "ar": "التجويد", "age": "Fluent readers",
     "text": "The rules of beautiful recitation: makharij, ghunnah, madd and more, practised aloud with the teacher."},
    {"key": "hifz", "name": "Hifz", "ar": "الحفظ", "age": "Committed students",
     "text": "Memorising the Quran with a structured daily plan of new lessons (sabaq) and revision (muraja'ah)."},
]

ALONGSIDE = [
    {"name": "Arabic language", "ar": "اللغة العربية",
     "text": "Quranic and conversational Arabic, so children understand what they recite."},
    {"name": "Islamic studies", "ar": "الدراسات الإسلامية",
     "text": "Duas, salah, seerah and good character, taught in a way children enjoy."},
]

PACKAGES = [
    {"name": "15-day starter", "rhythm": "Every day for 15 days", "best": "Trying a teacher, or a holiday boost"},
    {"name": "Weekly", "rhythm": "2, 3 or 5 days a week", "best": "Steady progress alongside school"},
    {"name": "Alternate days", "rhythm": "Every other day", "best": "Younger children and busy families"},
    {"name": "Your own schedule", "rhythm": "You choose the days and times", "best": "Hifz students and adults"},
]

PROMISES = [
    {"title": "Every teacher is tested", "text": "Our Head of Academics, a Hafiza of the Quran, listens to each teacher's recitation and watches a trial lesson before they can teach."},
    {"title": "Female teachers on request", "text": "Choose a male or female teacher. Girls and mothers can learn with a female teacher only."},
    {"title": "Parents can always watch", "text": "Classes run in our own video room. You can join any lesson, and you see a short progress note after each one."},
    {"title": "Your payment is protected", "text": "You pay us, not the teacher. We release the teacher's pay only for classes that actually took place. Missed classes are credited back."},
    {"title": "Times that suit your time zone", "text": "Families in Canada, the US, the UK and the Gulf are matched with teachers whose hours fit their evenings and weekends."},
]

TEACHER_POINTS = [
    "Paid on time, every week, for every class you teach",
    "Students come to you; no chasing families for fees",
    "Teach from home in Pakistan, Egypt or anywhere",
    "Choose your own hours and levels",
]

TEACHER_STEPS = [
    {"title": "Apply online", "text": "Tell us about your ijazah, certificates and teaching experience."},
    {"title": "Send a recitation", "text": "Our Head of Academics reviews your recitation and tajweed."},
    {"title": "Interview and trial lesson", "text": "A short video call and a demonstration lesson with a child."},
    {"title": "Checks and approval", "text": "ID and references are checked, as for anyone who teaches children. Then you receive your level badge."},
]

COUNTRIES = ["Canada", "United States", "United Kingdom", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait",
             "Bahrain", "Oman", "Pakistan", "India", "Egypt", "Australia", "Other"]

COURSE_CHOICES = [p["name"] for p in PATH] + [a["name"] for a in ALONGSIDE] + ["Not sure yet"]

# Short videos (YouTube Shorts / TikTok). Add an entry once a video is uploaded; "youtube" is the video ID.
VIDEOS: list[dict] = []

DAWAH_INTERESTS = ["I am curious about Islam", "I am thinking of becoming Muslim", "I would like to say the Shahada",
                   "I am a new Muslim", "I am asking for someone else"]

# Languages people speak. Asked of families and teachers so we can match them and sort our records.
LANGUAGE_CHOICES = ["English", "Urdu", "Arabic", "Hindi", "Punjabi", "Pashto", "Sindhi", "Bengali", "Malay", "Indonesian",
                    "Turkish", "Persian (Farsi)", "Somali", "Swahili", "French", "Spanish", "Other"]
LEVELS = ["Native", "Fluent", "Good", "Basic"]
LEVELS_WITH_NONE = LEVELS + ["None"]
# The language a teacher uses to explain the lesson
INSTRUCTION_LANGS = ["English", "Urdu", "Arabic", "Hindi", "Malay", "Indonesian", "French", "Spanish", "Any"]
