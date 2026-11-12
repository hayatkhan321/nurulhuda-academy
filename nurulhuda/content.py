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

# Free Quran downloads. We link to the publishers' own files rather than copying them, so each family always
# gets the latest corrected edition. QuranEnc.com allows re-publishing unchanged with credit; the others we link.
QURAN_RESOURCES = [
    {"lang": "English", "native": "English", "title": "The Noble Quran, Saheeh International",
     "note": "Clear modern English, widely used in classes.", "source": "IslamHouse.com",
     "pdf": "https://d1.islamhouse.com/data/en/ih_books/single2/en-translation-of-the-meanings-of-the-quran.pdf", "size": "22 MB",
     "page": "https://islamhouse.com/en/books/78592/"},
    {"lang": "English", "native": "English", "title": "Translation by the Rowwad Translation Center",
     "note": "Arabic and English side by side. Also a version for phones.", "source": "QuranEnc.com",
     "pdf": "https://quranenc.com/downloads/pdf/english_rwwad.pdf", "size": "",
     "page": "https://quranenc.com/en/browse/english_rwwad"},
    {"lang": "Urdu", "native": "اردو", "title": "قرآن کریم مع اردو ترجمہ و تفسیر: مولانا محمد جوناگڑھی، صلاح الدین یوسف",
     "note": "Urdu translation with short commentary, from the King Fahd Complex.", "source": "IslamHouse.com",
     "pdf": "https://d1.islamhouse.com/data/ur/ih_books/single/ur_translation_of_the_meaning_of_the_Holy_Quran_in_Urdu.pdf", "size": "36 MB",
     "page": "https://islamhouse.com/en/books/93/"},
    {"lang": "Hindi", "native": "हिन्दी", "title": "क़ुरआन मजीद, हिन्दी अनुवाद",
     "note": "The King Fahd Complex edition. A large file: best downloaded on Wi-Fi.", "source": "King Fahd Complex, via Internet Archive",
     "pdf": "https://archive.org/download/QuranInTheHindi-KingFahadComplex/Translation%20of%20the%20meanings%20of%20the%20Noble%20Quran%20in%20the%20Hindi%20-%20King%20Fahad%20Complex.pdf", "size": "164 MB",
     "page": "https://quranenc.com/hi/browse/hindi_omari"},
    {"lang": "Malay", "native": "Bahasa Melayu", "title": "Terjemahan Makna Al-Quran Al-Karim ke Bahasa Melayu",
     "note": "The King Fahd Complex edition. A large file: best downloaded on Wi-Fi.", "source": "King Fahd Complex, via Internet Archive",
     "pdf": "https://archive.org/download/quranmelayu/Terjemahan%20Makna%20Al%20Quran%20Al%20Karim%20Ke%20Bahasa%20Melayu_text.pdf", "size": "125 MB",
     "page": "https://quranenc.com/en/browse/malay_basumayyah"},
    {"lang": "Indonesian", "native": "Bahasa Indonesia", "title": "Al-Qur'an dan Terjemahnya",
     "note": "The King Fahd Complex edition. A large file: best downloaded on Wi-Fi.", "source": "King Fahd Complex, via Internet Archive",
     "pdf": "https://archive.org/download/quran_indonesian/Terjemah%20Makna%20Al%20Qur%27an%20Bahasa%20Indonesia.pdf", "size": "300 MB",
     "page": "https://quranenc.com/id/browse/indonesian_affairs"},
    {"lang": "French", "native": "Français", "title": "Traduction de Rachid Maach",
     "note": "Arabe et français côte à côte.", "source": "QuranEnc.com",
     "pdf": "https://quranenc.com/downloads/pdf/french_rashid.pdf", "size": "",
     "page": "https://quranenc.com/fr/browse/french_rashid"},
    {"lang": "Spanish", "native": "Español", "title": "Traducción de Muhammad Isa García",
     "note": "Árabe y español lado a lado.", "source": "QuranEnc.com",
     "pdf": "https://quranenc.com/downloads/pdf/spanish_garcia.pdf", "size": "",
     "page": "https://quranenc.com/es/browse/spanish_garcia"},
]
# Every language, with audio, in one place
QURAN_ONLINE = [
    {"name": "Quran.com", "url": "https://quran.com", "text": "Read and listen in dozens of languages, on any phone."},
    {"name": "QuranEnc.com", "url": "https://quranenc.com", "text": "Reviewed translations in over 70 languages, free to download."},
]

# Why we read the Quran. Only well-known, authentic texts, each with its reference.
QURAN_VERSES = [
    {"text": "Indeed, this Quran guides to that which is most upright.", "ref": "Quran 17:9"},
    {"text": "And We have certainly made the Quran easy to remember, so is there anyone who will be mindful?", "ref": "Quran 54:17"},
    {"text": "A blessed Book which We have revealed to you, that they might reflect upon its verses and that those of understanding would be reminded.", "ref": "Quran 38:29"},
]
HADITH = [
    {"text": "The best of you are those who learn the Quran and teach it.", "ref": "Sahih al-Bukhari 5027"},
    {"text": "The one who is skilled in the Quran will be with the noble and righteous scribes (the angels). And the one who recites the Quran and stumbles over it, finding it difficult, will have a double reward.", "ref": "Sahih al-Bukhari 4937, Sahih Muslim 798"},
    {"text": "Recite the Quran, for on the Day of Resurrection it will come as an intercessor for its companions.", "ref": "Sahih Muslim 804"},
    {"text": "Whoever reads a letter from the Book of Allah will have a good deed, and a good deed is rewarded tenfold. I do not say that Alif Lam Mim is one letter; rather Alif is a letter, Lam is a letter and Mim is a letter.", "ref": "Jami' at-Tirmidhi 2910, graded hasan sahih"},
    {"text": "It will be said to the companion of the Quran: Recite and rise, and recite slowly as you used to recite in the world, for your place will be at the last verse you recite.", "ref": "Sunan Abi Dawud 1464, Jami' at-Tirmidhi 2914"},
    {"text": "No people gather in one of the houses of Allah, reciting the Book of Allah and studying it together, except that tranquillity descends upon them, mercy covers them, the angels surround them, and Allah mentions them to those who are with Him.", "ref": "Sahih Muslim 2699"},
    {"text": "The example of a believer who recites the Quran is like a citron: its fragrance is pleasant and its taste is pleasant.", "ref": "Sahih al-Bukhari 5020, Sahih Muslim 797"},
    {"text": "Allah raises some people by this Book and lowers others by it.", "ref": "Sahih Muslim 817"},
]
# For families: the Quran in the home and in marriage
FAMILY_TEXTS = [
    {"text": "A woman is married for four things: her wealth, her lineage, her beauty and her religion. Choose the one with religion, may your hands be blessed.", "ref": "Sahih al-Bukhari 5090, Sahih Muslim 1466"},
    {"text": "This world is provision, and the best provision of this world is a righteous woman.", "ref": "Sahih Muslim 1467"},
    {"text": "May Allah have mercy on a man who gets up at night to pray and wakes his wife, and may Allah have mercy on a woman who gets up at night to pray and wakes her husband.", "ref": "Sunan Abi Dawud 1308, Sunan an-Nasa'i 1610"},
    {"text": "The Quran will meet its companion on the Day of Resurrection, and his parents will be clothed in two garments that the whole world cannot match. They will ask: Why have we been given these? It will be said: Because your child carried the Quran.", "ref": "Musnad Ahmad and Sunan Ibn Majah, from Buraydah; Ibn Kathir graded its chain hasan (Tafsir Ibn Kathir, virtues of Surah al-Baqarah). Narration abridged."},
]

# The Quran one juz (para) at a time, for class. Opens in the publisher's own viewer.
JUZ_SOURCE = {"indopak": "https://islamicstudies.info/viewer/web/viewer.html?file=/quran/juz/{n}.pdf",
              "madinah": "https://islamicstudies.info/viewer/web/viewer.html?file=/quran/mushaf/Quran-Al-Madina-Juz-{n}.pdf",
              "source": "IslamicStudies.info", "page": "https://www.islamicstudies.info/quran/juz"}

# Learning material, linked from the publishers' own pages.
EARLY_RESOURCES = [
    {"title": "Noorani Qaida (English)", "note": "The first book: Arabic letters, joining and harakat. Read online, page by page.",
     "url": "https://kidsquranreading.com/noorani-qaida-in-english.htm", "source": "KidsQuranReading.com"},
    {"title": "Noorani Qaida (Urdu)", "note": "The same Qaida with Urdu explanations, as used in Pakistan and India.",
     "url": "https://www.kidsquranreading.com/noorani-qaida-in-urdu.htm", "source": "KidsQuranReading.com"},
    {"title": "Yassarnal Quran (Urdu)", "note": "The simple first-lessons primer used across Pakistan and India, from the letters to reading whole verses. Qudratullah Company edition.",
     "url": "https://archive.org/download/yassernal-quran/Yassernal%20Quran.pdf", "source": "Qudratullah Company, via Internet Archive", "size": "17 MB"},
    {"title": "Quran.com word by word", "note": "Tap any word to hear it and see its meaning. Good for practice at home.",
     "url": "https://quran.com", "source": "Quran.com"},
]
MEDIUM_RESOURCES = [
    {"title": "Tajweed Rules of the Qur'an", "note": "A clear English guide to the rules of recitation, for students who already read fluently.",
     "url": "https://d1.islamhouse.com/data/en/ih_books/single2/en_Tajweed_Rules_of_the_Quran_Part_01.pdf", "source": "IslamHouse.com"},
    {"title": "A Guide for the Reciter (Murshid al-Qari), Part 1", "note": "A short tajweed workbook by Saleem Gaibie, Al-Tanzil Institute of Quranic Sciences.",
     "url": "https://duai.org.za/wp-content/uploads/2023/02/Murshid-al-Qari-Part-1-Simplifying-the-rules-of-Tajweed.pdf", "source": "duai.org.za"},
]
DUA_RESOURCES = [
    {"lang": "English", "url": "https://d1.islamhouse.com/data/en/ih_books/single/risala_en_hisnulmuslim.pdf", "size": "2 MB"},
    {"lang": "اردو", "url": "https://d1.islamhouse.com/data/ur/ih_books/single/risala_ur_hisnul_muslim.pdf", "size": "10 MB"},
    {"lang": "हिन्दी", "url": "https://d1.islamhouse.com/data/hi/ih_books/single/risala_hi_hisnul-muslim_4.0.pdf", "size": "3 MB"},
    {"lang": "Bahasa Melayu", "url": "https://d1.islamhouse.com/data/ms/ih_books/single/ms_hisn_muslim.pdf", "size": "2 MB"},
    {"lang": "Bahasa Indonesia", "url": "https://d1.islamhouse.com/data/id/ih_books/single/risala_id_hisnulmuslim.pdf", "size": "2 MB"},
    {"lang": "Español", "url": "https://d1.islamhouse.com/data/es/ih_books/single/risala_es_hisnul_muslim.pdf", "size": "2 MB"},
    {"lang": "Français", "url": "https://d1.islamhouse.com/data/fr/ih_books/single/risala_fr_hisnulmuslim.pdf", "size": "2 MB"},
]
