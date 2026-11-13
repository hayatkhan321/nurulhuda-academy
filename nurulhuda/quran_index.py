"""Quran positions for progress bars (King Fahd Complex Hafs v18 numbering). Generated from hafsData_v18.json."""
from bisect import bisect_right

VERSES = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6]  # verses in each surah, 1 to 114
NAMES = ["Al-Fātiḥah", "Al-Baqarah", "Āl-‘Imrān", "An-Nisā’", "Al-Mā’idah", "Al-An‘ām", "Al-A‘rāf", "Al-Anfāl", "At-Taubah", "Yūnus", "Hūd", "Yūsuf", "Ar-Ra‘d", "Ibrāhīm", "Al-Ḥijr", "An-Naḥl", "Al-Isrā’", "Al-Kahf", "Maryam", "Ṭā-Hā", "Al-Anbiyā’", "Al-Ḥajj", "Al-Mu’minūn", "An-Nūr", "Al-Furqān", "Ash-Shu‘arā’", "An-Naml", "Al-Qaṣaṣ", "Al-‘Ankabūt", "Ar-Rūm", "Luqmān", "As-Sajdah", "Al-Aḥzāb", "Saba’", "Fāṭir", "Yā-Sīn", "Aṣ-Ṣāffāt", "Ṣād", "Az-Zumar", "Ghāfir", "Fuṣṣilat", "Ash-Shūra", "Az-Zukhruf", "Ad-Dukhān", "Al-Jāthiyah", "Al-Aḥqāf", "Muḥammad", "Al-Fatḥ", "Al-Ḥujurāt", "Qāf", "Adh-Dhāriyāt", "Aṭ-Ṭūr", "An-Najm", "Al-Qamar", "Ar-Raḥmān", "Al-Wāqi‘ah", "Al-Ḥadīd", "Al-Mujādilah", "Al-Ḥashr", "Al-Mumtaḥanah", "Aṣ-Ṣaff", "Al-Jumu‘ah", "Al-Munāfiqūn", "At-Taghābun", "Aṭ-Ṭalāq", "At-Taḥrīm", "Al-Mulk", "Al-Qalam", "Al-Ḥāqqah", "Al-Ma‘ārij", "Nūḥ", "Al-Jinn", "Al-Muzzammil", "Al-Muddaththir", "Al-Qiyāmah", "Al-Insān", "Al-Mursalāt", "An-Naba’", "An-Nāzi‘āt", "‘Abasa", "At-Takwīr", "Al-Infiṭār", "Al-Muṭaffifīn", "Al-Inshiqāq", "Al-Burūj", "Aṭ-Ṭāriq", "Al-A‘lā", "Al-Ghāshiyah", "Al-Fajr", "Al-Balad", "Ash-Shams", "Al-Lail", "Aḍ-Ḍuḥā", "Ash-Sharḥ", "At-Tīn", "Al-‘Alaq", "Al-Qadr", "Al-Bayyinah", "Az-Zalzalah", "Al-‘Ādiyāt", "Al-Qāri‘ah", "At-Takāthur", "Al-‘Aṣr", "Al-Humazah", "Al-Fīl", "Quraish", "Al-Mā‘ūn", "Al-Kauthar", "Al-Kāfirūn", "An-Naṣr", "Al-Masad", "Al-Ikhlāṣ", "Al-Falaq", "An-Nās"]
JUZ_START = [(1, 1), (2, 142), (2, 253), (3, 92), (4, 24), (4, 148), (5, 82), (6, 111), (7, 88), (8, 41), (9, 94), (11, 6), (12, 53), (15, 1), (17, 1), (18, 75), (21, 1), (23, 1), (25, 21), (27, 56), (29, 46), (33, 31), (36, 28), (39, 32), (41, 47), (46, 1), (51, 31), (58, 1), (67, 1), (78, 1)]  # (surah, verse) where each juz begins
TOTAL = 6236
_START = [0]
for _n in VERSES:
    _START.append(_START[-1] + _n)


def index(surah: int, verse: int) -> int:
    """0-based position of a verse in the whole Quran."""
    surah = max(1, min(114, surah))
    verse = max(1, min(VERSES[surah - 1], verse))
    return _START[surah - 1] + verse - 1


_JUZ_IDX = [index(s, v) for s, v in JUZ_START] + [TOTAL]


def juz_of(surah: int, verse: int) -> int:
    return max(1, min(30, bisect_right(_JUZ_IDX, index(surah, verse))))


def juz_progress(surah: int, verse: int) -> tuple[int, int]:
    """(juz number, percent of that juz read up to and including this verse)."""
    i = index(surah, verse)
    j = max(1, min(30, bisect_right(_JUZ_IDX, i)))
    lo, hi = _JUZ_IDX[j - 1], _JUZ_IDX[j]
    return j, round((i - lo + 1) / (hi - lo) * 100)


def quran_percent(surah: int, verse: int) -> float:
    return round((index(surah, verse) + 1) / TOTAL * 100, 1)
