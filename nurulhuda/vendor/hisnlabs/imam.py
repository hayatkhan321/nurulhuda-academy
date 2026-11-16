# The "imam": turns what the model heard (Quran phonetic script + sifat) into per-word tajweed remarks, the way a
# teacher would correct a student: «لَنَآ: المد المنفصل حركتان بدل أربع», «ٱلْغُيُوبِ: القلقلة غير ظاهرة».
#
#   ref  = expected(uthmani_words)          what a correct Hafs recitation of exactly these words sounds like
#                                           (the last word in its waqf form, a hamzat wasl at the start voiced)
#   notes = listen(ref, heard_phonemes, heard_sifat=None)
#
# How: the phonetizer maps every Uthmani letter to its span of phonetic script and tags the madd / qalqalah rules.
# The heard script is aligned to the expected one letter by letter; every rule span is then read in the heard script
# (madd = how many times the long vowel repeats, ghunnah = how long the nasal is held, ں = ikhfa, ۾ = iqlab, ڇ =
# qalqalah, a doubled letter after a vanished nun = idgham). What is left over (another letter, another vowel, a
# missing letter) is a clear mistake (لحن جلي); length, ghunnah, qalqalah and tafkhim are the fine points (لحن خفي).
# Lengths are judged with ±1 count of tolerance: the teacher model itself is right within ±1 count 95.5 % of the time.
from dataclasses import dataclass, field
import Levenshtein
from quran_transcript import quran_phonetizer, MoshafAttributes

LONG = {'ا': 'alif', 'ۥ': 'waw', 'ۦ': 'yaa'}
ONSET = 3  # symbols at the start of a breath where "another letter / dropped sound" is not judged
HARAKAT = set('َُِ')
NASAL = set('نم')
SIFAT = ['hams_or_jahr', 'shidda_or_rakhawa', 'tafkheem_or_taqeeq', 'itbaq', 'safeer', 'qalqla', 'tikraar', 'tafashie',
         'istitala', 'ghonna']

# Hafs ʿan ʿAsim: the lengths a teacher accepts (the ṭuruq of the Shatibiyya and the Tayyiba)
MADD = {  # rule class → (allowed counts, ar, en, fr)
    'NormalMaddRule': ({2}, 'المد الطبيعي', 'natural madd', 'madd naturel'),
    'MonfaselMaddRule': ({2, 4, 5}, 'المد المنفصل', 'separated madd (munfasil)', 'madd munfasil'),
    'MottaselMaddRule': ({4, 5, 6}, 'المد المتصل', 'joined madd (muttasil)', 'madd muttasil'),
    'MottaselMaddPauseRule': ({4, 5, 6}, 'المد المتصل وقفا', 'joined madd at a stop', 'madd muttasil à l’arrêt'),
    'LazemMaddRule': ({6}, 'المد اللازم', 'necessary madd (lazim)', 'madd lazim'),
    'AaredMaddRule': ({2, 4, 6}, 'المد العارض للسكون', 'madd before a stop (ʿarid)', 'madd ʿarid (à l’arrêt)'),
    'LeenMaddRule': ({2, 4, 6}, 'مد اللين', 'soft madd (lin)', 'madd lin'),
    'BadalMadd': ({2}, 'مد البدل', 'madd after a hamza (badal)', 'madd badal'),
    'LeenHamzaMadd': ({4, 6}, 'مد اللين المهموز', 'soft madd before a hamza (lin)', 'madd lin devant une hamza'),
}
# Warsh ʿan Nāfiʿ (al-Azraq): munfasil and muttasil 6, badal 2 / 4 / 6 (Hafs: a plain natural madd).
# The models write a long munfasil / muttasil as 4 whatever its real length (43/43 on the Warsh professionals): 4 to 6
# pass, only a short one (2: Hafs's qasr, Qalun's) is corrected, and the remark asks for Warsh's 6.
RIWAYAT = ('hafs', 'warsh')
WARSH_GOLDEN = {'MonfaselMaddRule': 6, 'MottaselMaddRule': 6, 'MottaselMaddPauseRule': 6}
WARSH_ALLOWED = {'NormalMaddRule': {2}, 'MonfaselMaddRule': {4, 5, 6}, 'MottaselMaddRule': {4, 5, 6}, 'MottaselMaddPauseRule': {4, 5, 6},
                 'LazemMaddRule': {6}, 'AaredMaddRule': {2, 4, 6}, 'LeenMaddRule': {2, 4, 6}, 'BadalMadd': {2, 4, 6},
                 'LeenHamzaMadd': {4, 6}}
# Madd length from time: the model writes at most 4 counts of a long madd (a held 6 comes out as 4, like a 5): when it
# writes 4 or 5, the length is measured in seconds against the reciter's own natural madd (2 counts) — the way a teacher
# counts with the student's own pace. Calibrated on qdat (159 learners, human labels: the 6 / 6 held munfasil found,
# none by the symbols) and the Warsh professionals (munfasil / muttasil 6 found 18 / 22): in natural-madd units × 2,
# ≥ 8.3 is a 6, 7.0–8.3 a 5 (passes for a 4 and a 6), below a 4.
TIME_SIX, TIME_FIVE = 8.3, 7.0
# the phonetizer is Hafs-only: Warsh's text (warsh.phrase) with the longest lengths it writes (munfasil 5 ≈ Warsh's 6)
WARSH_MOSHAF = dict(madd_monfasel_len=5, madd_mottasel_len=6, madd_mottasel_waqf=6, madd_aared_len=4)
WORDS = {'ar': {2: 'حركتان', 3: 'ثلاث حركات', 4: 'أربع حركات', 5: 'خمس حركات', 6: 'ست حركات'},
         'en': 'counts', 'fr': 'temps'}

def counts(n, lang):
    if lang == 'ar': return WORDS['ar'].get(n, f'{n} حركات') if n else 'بلا مد'
    return f"{n} {WORDS[lang]}"

def default_moshaf(**kw):
    a = dict(rewaya='hafs', madd_monfasel_len=4, madd_mottasel_len=4, madd_mottasel_waqf=4, madd_aared_len=4)
    a.update(kw); return MoshafAttributes(**a)


@dataclass
class Unit:  # one thing a teacher listens for, at [s, e) of the expected script
    s: int; e: int; kind: str; word: int
    golden: int = 0; allowed: set = field(default_factory=set); rule: str = ''; char: str = ''


@dataclass
class Ref:
    words: list            # Uthmani words
    phonemes: str          # expected phonetic script (no spaces)
    spans: list            # per word: [s, e) in phonemes
    units: list
    sifat: list            # phonetizer SifaOutput per sound group
    index: list = None     # per word: its index in the passage (a word repeated after a stop appears twice)
    stops: list = None     # passage indices of the words the reciter stopped on (waqf)
    restarts: list = None  # passage index each new breath started from (ibtida)
    ends: list = None      # positions in `words` where a breath ends (the last word of each breath)
    riwaya: str = 'hafs'


def expected(words, moshaf=None, riwaya='hafs'):
    """words: the Uthmani words actually recited (a whole aya or the part between two pauses), phonetizer spelling
    (Warsh: the words of the Warsh mushaf through warsh.phrase)"""
    text = ' '.join(words)
    warsh = riwaya == 'warsh'
    o = quran_phonetizer(text, moshaf or default_moshaf(**(WARSH_MOSHAF if warsh else {})), remove_spaces=True)
    ph, mp = o.phonemes, o.mappings
    # word spans: union of the spans of its letters; letters that vanish (hamzat wasl, the nun of an idgham) give
    # an empty span and are skipped
    spans, pos = [], 0
    for w in words:
        ps = [m.pos for m in mp[pos:pos + len(w)] if m.pos[1] > m.pos[0]]
        spans.append((min(p[0] for p in ps), max(p[1] for p in ps)) if ps else (spans[-1][1] if spans else 0,) * 2)
        pos += len(w) + 1
    word_at = lambda i: next((k for k, (a, b) in enumerate(spans) if a <= i < b), len(spans) - 1)
    # did the word end with a nun / tanween that disappears into the next word (idgham)?
    vanishing = [any(m.deleted for m in mp[p0:p0 + len(w)][-3:]) and (w.rstrip('ْۡ').endswith('ن') or any(c in w for c in 'ًࣰٌࣱٍࣲ'))
                 for w, p0 in zip(words, [sum(len(x) + 1 for x in words[:k]) for k in range(len(words))])]

    units, ruled = [], set()
    for m in mp:  # tagged rules: every madd, qalqalah
        for r in m.tajweed_rules or []:
            a, b = m.pos
            name = type(r).__name__
            if name in MADD:
                seg = ph[a:b]
                c = next((ch for ch in seg if ch in LONG), None) or (seg[0] if name == 'LeenMaddRule' else None)
                if c is None: continue
                # the counts actually written: the long vowel repeated (+1 for a lin: its و/ي is the first count)
                j = seg.index(c); k = j
                while k < len(seg) and seg[k] == c: k += 1
                allowed = MADD[name][0]
                if warsh:
                    # badal: a natural madd right after a hamza (ءَامَنُوا, إِيمَٰن, أُوتُوا)
                    w_ = word_at(a)
                    if name == 'NormalMaddRule' and a + j >= 2 and ph[a + j - 2] == 'ء' and ph[a + j - 1] in HARAKAT:
                        name = 'BadalMadd'
                    # after naql into the article the hamza is gone but the madd is still a badal: ٱلَاخِرَةِ (lākhira)
                    elif name == 'NormalMaddRule' and a + j >= 2 and ph[a + j - 2] == 'ل' and 'ٱلَا' in words[w_] \
                            and ph.find('لَا', spans[w_][0]) == a + j - 2:
                        name = 'BadalMadd'
                    allowed = WARSH_ALLOWED[name]
                golden = k - j + (name == 'LeenMaddRule')
                units.append(Unit(a + j, a + k, 'madd', word_at(a), golden=WARSH_GOLDEN.get(name, golden) if warsh else golden,
                                  allowed=allowed, rule=name, char=c))
                ruled.update(range(a + j, a + k))
            elif name == 'Qalqalah':
                q = ph.find('ڇ', a, b)
                if q >= 0: units.append(Unit(q, q + 1, 'qalqalah', word_at(q), char='ڇ')); ruled.add(q)
    if warsh:  # lin before a hamza in the same word (شَيْءٍ, سَوْءَ): Warsh lengthens it, 4 or 6
        for i in range(1, len(ph) - 1):
            if ph[i] in 'يو' and ph[i - 1] == 'َ' and ph[i + 1] == 'ء' and i not in ruled and word_at(i) == word_at(i + 1):
                units.append(Unit(i, i + 1, 'madd', word_at(i), golden=4, allowed=WARSH_ALLOWED['LeenHamzaMadd'],
                                  rule='LeenHamzaMadd', char=ph[i]))
                ruled.add(i)
    i = 0
    while i < len(ph):  # untagged rules, read from the script itself
        j = i
        while j < len(ph) and ph[j] == ph[i]: j += 1
        c, n, w = ph[i], j - i, word_at(i)
        if i not in ruled:
            if c == 'ں': units.append(Unit(i, j, 'ikhfa', w, golden=n, char=c))
            elif c == '۾': units.append(Unit(i, j, 'iqlab', w, golden=n, char=c))
            elif c in NASAL and n >= 3:  # ننننَ / ممممِ : nun / mim with shadda, or a nun merged into ن / م
                prev_w = word_at(i - 1) if i else w
                kind = 'idgham_ghunnah' if (prev_w != w and vanishing[prev_w]) else 'ghunnah'
                units.append(Unit(i, j, kind, prev_w if kind == 'idgham_ghunnah' else w, golden=n, char=c))
            elif c in 'يو' and n >= 3:  # «مَن يَقُولُ» → مَيييَقُ : nun merged into ي / و with ghunnah
                units.append(Unit(i, j, 'idgham_ghunnah', w, golden=n, char=c))
            elif c not in LONG and c not in HARAKAT and n == 2:  # a doubled letter: shadda, or idgham without ghunnah
                prev_w = word_at(i - 1) if i else w
                if i == spans[w][0] and prev_w != w and vanishing[prev_w]:
                    units.append(Unit(i, j, 'idgham', prev_w, golden=2, char=c))
                else:
                    units.append(Unit(i, j, 'shadda', w, golden=2, char=c))
        i = j
    units.sort(key=lambda u: u.s)
    return Ref(list(words), ph, spans, units, o.sifat, list(range(len(words))), [], [0], [len(words) - 1], riwaya)


def _join(parts):
    """one Ref out of several breaths: (Ref, first passage index) pairs, in the order recited"""
    words, ph, spans, units, sifat, index = [], '', [], [], [], []
    for r, a in parts:
        o, w0 = len(ph), len(words)
        words += r.words; index += [a + k for k in range(len(r.words))]
        spans += [(x + o, y + o) for x, y in r.spans]
        units += [Unit(u.s + o, u.e + o, u.kind, u.word + w0, u.golden, u.allowed, u.rule, u.char) for u in r.units]
        sifat += r.sifat; ph += r.phonemes
    ends, k = [], 0
    for r, _ in parts:
        k += len(r.words); ends.append(k - 1)
    return Ref(words, ph, spans, units, sifat, index, [index[e] for e in ends[:-1]], [a for _, a in parts], ends,
               parts[0][0].riwaya if parts else 'hafs')


def recited(words, heard, moshaf=None, back=4, margin=3, riwaya='hafs'):
    """The passage as the reciter actually delivered it: where they stopped (waqf: the word takes its pausal form,
    tanween → alif or silence, ة → ه, silat al-ha' dropped...) and where they started again (ibtida: often a few words
    back). Each breath is judged against its own reference, so a correct stop is not taken for a mistake.
    Greedy search: split a breath wherever it brings the expected script clearly closer to what was heard."""
    heard = heard.replace(' ', '')
    cache = {}
    def ref(a, b):
        if (a, b) not in cache: cache[(a, b)] = expected(words[a:b], moshaf, riwaya)
        return cache[(a, b)]
    def cost(phr): return Levenshtein.distance(''.join(ref(a, b).phonemes for a, b in phr), heard)
    phr = [(0, len(words))]
    best = cost(phr)
    while True:
        cands = []
        for i, (a, b) in enumerate(phr):
            for k in range(a + 1, b):              # stop after word k-1 ...
                for j in range(max(a + 1, k - back), k + 1):  # ... start again from word j (j < k: repeat)
                    cands.append(phr[:i] + [(a, k), (j, b)] + phr[i + 1:])
        if not cands: break
        c, new = min((cost(x), x) for x in cands)
        if c > best - margin: break                # a split must explain at least `margin` sounds better
        best, phr = c, new
    return _join([(ref(a, b), a) for a, b in phr])


def _boundaries(ref, heard):
    """b[i] = position in the heard script that corresponds to position i of the expected one"""
    b = [0] * (len(ref) + 1)
    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(ref, heard):
        for k in range(i1, i2 + 1):
            b[k] = j1 + (round((k - i1) * (j2 - j1) / (i2 - i1)) if i2 > i1 else 0)
    b[len(ref)] = len(heard)
    return b


def _run(heard, a, b, c):
    """the run of c in heard[a:b], grown over its neighbours (an inserted extra count belongs to the run)"""
    k = next((x for x in range(a, b) if heard[x] == c), None)
    if k is None: return 0, a, a
    s = e = k
    while s > 0 and heard[s - 1] == c: s -= 1
    while e < len(heard) and heard[e] == c: e += 1
    return e - s, s, e


def _dur(heard, times, s, e):
    """seconds of the long vowel heard[s:e] (its short vowel included) up to the next sound"""
    a = times[s - 1] if s and heard[s - 1] in HARAKAT else times[s]
    return max(0.0, times[min(e, len(times) - 1)] - a)


def _tempo(ref, heard, b, times, tempo):
    """seconds per count: half the median natural madd of this phrase (not at the end of a breath, where a madd may be
    held as ʿarid), or of the session when the phrase has fewer than 2"""
    if not times or len(times) != len(heard) + 1: return None
    ends = {e for e in (ref.ends or [len(ref.words) - 1])}
    nat = []
    for u in ref.units:
        if u.kind == 'madd' and u.rule == 'NormalMaddRule' and u.word not in ends:
            n, s, e = _run(heard, max(0, b[u.s] - 1), min(len(heard), b[u.e] + 1), u.char)
            if 1 <= n <= 3: nat.append(_dur(heard, times, s, e))
    nat = [d for d in nat if 0.08 < d < 2.0]
    if tempo is not None:
        tempo.extend(nat); del tempo[:-40]
    src = nat if len(nat) >= 2 else (tempo or []) if tempo is not None and len(tempo) >= 3 else []
    if not src: return None
    srt = sorted(src)
    return srt[len(srt) // 2] / 2


def _msg(kind, lang, **k):
    T = {
        'madd_short': {'ar': '{name}: {heard} بدل {want}', 'en': '{name} too short: {heard} instead of {want}',
                       'fr': '{name} trop court : {heard} au lieu de {want}'},
        'madd_long': {'ar': '{name}: {heard} بدل {want}', 'en': '{name} too long: {heard} instead of {want}',
                      'fr': '{name} trop long : {heard} au lieu de {want}'},
        'madd_missing': {'ar': '{name}: المد محذوف', 'en': '{name} dropped: the vowel must be lengthened',
                         'fr': '{name} oublié : la voyelle doit être allongée'},
        'madd_added': {'ar': 'مد زائد في غير موضعه', 'en': 'a vowel lengthened where there is no madd',
                       'fr': 'une voyelle allongée là où il n’y a pas de madd'},
        'madd_uneven': {'ar': '{name}: سوِّ بين المدود ({lens})', 'en': '{name}: keep the same length every time ({lens})',
                        'fr': '{name} : garde la même longueur à chaque fois ({lens})'},
        'ghunnah_short': {'ar': 'الغنة ناقصة: أطِل الغنة حركتين', 'en': 'ghunnah too short: hold the nasal sound for 2 counts',
                          'fr': 'ghunna trop courte : tiens le son nasal 2 temps'},
        'ikhfa_izhar': {'ar': 'إخفاء: أظهرتَ النون، والصواب إخفاؤها مع الغنة', 'en': 'ikhfaʾ: the nun was pronounced clearly; hide it with ghunnah',
                        'fr': 'ikhfaʾ : le noun a été prononcé clairement ; il faut le cacher avec la ghunna'},
        'ikhfa_short': {'ar': 'إخفاء: الغنة قصيرة', 'en': 'ikhfaʾ: the ghunnah is too short', 'fr': 'ikhfaʾ : la ghunna est trop courte'},
        'iqlab_missed': {'ar': 'إقلاب: تُقلب النون ميمًا مخفاة مع الغنة', 'en': 'iqlab: the nun becomes a hidden mim with ghunnah before ب',
                         'fr': 'iqlab : le noun devient un mim caché avec ghunna devant ب'},
        'idgham_missed': {'ar': 'إدغام: أظهرتَ النون، والصواب إدغامها في {letter}', 'en': 'idgham: the nun was pronounced; merge it into {letter}',
                          'fr': 'idgham : le noun a été prononcé ; il faut le fondre dans {letter}'},
        'idgham_ghunnah_short': {'ar': 'إدغام بغنة: الغنة ناقصة', 'en': 'idgham with ghunnah: the ghunnah is missing',
                                 'fr': 'idgham avec ghunna : la ghunna manque'},
        'shadda_missing': {'ar': 'الشدة على {letter} غير ظاهرة', 'en': 'the shadda on {letter} was not pronounced',
                           'fr': 'la chadda sur {letter} n’a pas été prononcée'},
        'qalqalah_missing': {'ar': 'القلقلة غير ظاهرة على {letter}', 'en': 'qalqalah missing on {letter}: let it bounce',
                             'fr': 'qalqala absente sur {letter} : fais-la rebondir'},
        'letter': {'ar': 'نطقتَ {heard} بدل {want}', 'en': 'pronounced {heard} instead of {want}',
                   'fr': '{heard} prononcé au lieu de {want}'},
        'vowel': {'ar': 'الحركة: {heard} بدل {want}', 'en': 'wrong vowel: {heard} instead of {want}',
                  'fr': 'mauvaise voyelle : {heard} au lieu de {want}'},
        'dropped': {'ar': 'سقط حرف: {want}', 'en': 'a sound was dropped: {want}', 'fr': 'un son a été omis : {want}'},
        'added': {'ar': 'زيادة: {heard}', 'en': 'an extra sound: {heard}', 'fr': 'un son en trop : {heard}'},
        'word_missing': {'ar': 'لم تُقرأ هذه الكلمة', 'en': 'this word was not heard', 'fr': 'ce mot n’a pas été entendu'},
        'sifa': {'ar': '{letter}: {heard} بدل {want}', 'en': '{letter}: {heard_en} instead of {want_en}',
                 'fr': '{letter} : {heard_fr} au lieu de {want_fr}'},
    }
    return T[kind][lang].format(**k)

VOWEL_NAME = {'َ': ('فتحة', 'a (fatha)', 'a (fatha)'), 'ُ': ('ضمة', 'u (damma)', 'ou (damma)'), 'ِ': ('كسرة', 'i (kasra)', 'i (kasra)')}
SIFA_NAME = {  # only what a teacher corrects: tafkhim / tarqiq where it depends on the context (ر, the ل of «الله»,
    # the alif after them); the other sifat follow from the letter, and a wrong letter is already a remark
    'tafkheem_or_taqeeq': {'mofakham': ('تفخيم', 'heavy (tafkhim)', 'emphatique (tafkhim)'),
                           'moraqaq': ('ترقيق', 'light (tarqiq)', 'léger (tarqiq)'),
                           'low_mofakham': ('تفخيم خفيف', 'slightly heavy', 'légèrement emphatique')},
}
SIFA_LETTERS = set('رلا')


def listen(ref, heard, heard_sifat=None, langs=('ar', 'en', 'fr'), heard_probs=None, min_prob=0.7, min_prob_jali=None,
           heard_times=None, tempo=None):
    """heard_probs: the model's confidence for each heard symbol: a remark about sounds it is not sure of
    (< min_prob) is left out: better say nothing than correct a reciter who was right. A clear mistake (another letter,
    vowel or sound) asks for more: min_prob_jali (default: min_prob).
    heard: the phonetic script the model wrote (spaces ignored). heard_sifat: optional list of
    [group, hams_or_jahr, ...] (the teacher label format), one per sound group.
    heard_times: the time (s) of each heard symbol, plus the end of the last one (tajweed.hear): long madds are then
    measured in seconds. tempo: a list kept by the caller for the whole session (the natural madds heard so far), for a
    phrase with too few natural madds of its own.
    → one entry per word: {'word', 'index', 'ok', 'notes': [{'rule', 'severity', 'expected', 'heard', 'msg': {lang: text}}],
       'madd': [{'rule', 'heard': 2|4|6, 'name': {lang: text}}]}  (every madd other than the natural one, as heard)"""
    heard = heard.replace(' ', '')
    b = _boundaries(ref.phonemes, heard)
    notes = [[] for _ in ref.words]
    covered = [False] * len(ref.phonemes)

    pos = [None]  # where in the expected script the current remark is (for the UI to highlight the letter)
    span = [(0, 0)]  # the heard symbols the current remark is about

    def unsure(hs, he, thr=None):
        if not heard_probs: return False
        seg = heard_probs[max(0, hs - 1):min(len(heard_probs), he + 1)]
        return bool(seg) and min(seg) < (thr if thr is not None else min_prob)
    jali_thr = min_prob_jali if min_prob_jali is not None else min_prob

    def add(w, rule, sev, exp, got, kind, **k):
        if unsure(*span[0]): return
        notes[w].append({'rule': rule, 'severity': sev, 'expected': exp, 'heard': got, 'pos': pos[0],
                         'msg': {l: _msg(kind, l, **{a: v[l] if isinstance(v, dict) else v for a, v in k.items()}) for l in langs}})

    def more_nun(u, hs, he):  # the heard script has a nun the expected one has not (the nun was not merged)
        return heard[max(0, hs - 2):he].count('ن') > ref.phonemes[max(0, u.s - 2):u.e].count('ن')

    madd_seen = {}
    madd_heard = [[] for _ in ref.words]
    unit = _tempo(ref, heard, b, heard_times, tempo)
    for u in ref.units:
        for x in range(u.s, u.e): covered[x] = True
        hs, he = b[u.s], b[u.e]
        pos[0], span[0] = u.s, (hs, he)
        if u.kind == 'madd':
            n, rs, re_ = _run(heard, max(0, hs - 1), min(len(heard), he + 1), u.char)
            n += u.rule.startswith('Leen') and n > 0
            sym, allowed, shown = n, u.allowed, (2 if n <= 3 else 4 if n <= 5 else 6) if n else 0
            if unit and n in (4, 5):  # the symbols stop at 4: the clock says 4, 5 or 6
                tc = _dur(heard, heard_times, rs, re_) / unit
                n = 6 if tc >= TIME_SIX else 5 if tc >= TIME_FIVE else 4
                shown = 6 if tc >= TIME_SIX else 4
                if ref.riwaya == 'warsh' and u.rule in WARSH_GOLDEN:
                    allowed = {6}  # measured: Warsh's 6 is asked for
                    shown = 6 if tc >= TIME_FIVE else 4  # a 5 passes for Warsh's 6: shown as the 6 it is taken for
            name = MADD[u.rule]
            near = min(allowed, key=lambda a: abs(a - n))
            madd_seen.setdefault(u.rule, []).append((u.word, sym))
            if shown and u.rule != 'NormalMaddRule':
                madd_heard[u.word].append({'rule': u.rule, 'heard': shown, 'name': {l: name_l(name, l) for l in langs}})
            if n == 0 and not u.rule.startswith('Leen'):
                add(u.word, u.rule, 'jali', u.golden, 0, 'madd_missing', name={l: name_l(name, l) for l in langs})
            elif abs(n - near) > 1 and not unsure(hs, he):
                long_ = n > near
                for_l = {l: dict(name=name_l(name, l), heard=counts(n, l), want=counts(u.golden if u.golden in u.allowed else near, l)) for l in langs}
                notes[u.word].append({'rule': u.rule, 'severity': 'khafi', 'expected': sorted(allowed), 'heard': n, 'pos': u.s,
                                      'msg': {l: _msg('madd_long' if long_ else 'madd_short', l, **for_l[l]) for l in langs}})
        elif u.kind == 'qalqalah':
            if 'ڇ' not in heard[max(0, hs - 1):he + 1]:
                letter = ref.phonemes[u.s - 1] if u.s else ''
                add(u.word, 'qalqalah', 'khafi', 'ڇ', '', 'qalqalah_missing', letter=letter)
        elif u.kind == 'ikhfa':
            n, _, _ = _run(heard, hs, max(he, hs + 1), 'ں')
            if n == 0 and 'ن' in heard[hs:he + 1]: add(u.word, 'ikhfa', 'khafi', u.golden, 0, 'ikhfa_izhar')
            elif n and n < u.golden - 1: add(u.word, 'ikhfa', 'khafi', u.golden, n, 'ikhfa_short')
        elif u.kind == 'iqlab':
            if '۾' not in heard[max(0, hs - 1):he + 1]: add(u.word, 'iqlab', 'khafi', u.golden, 0, 'iqlab_missed')
        elif u.kind in ('ghunnah', 'idgham_ghunnah'):
            n, _, _ = _run(heard, max(0, hs - 1), min(len(heard), he + 1), u.char)
            if u.kind == 'idgham_ghunnah' and u.char != 'ن' and more_nun(u, hs, he):
                add(u.word, 'idgham', 'khafi', u.golden, n, 'idgham_missed', letter=u.char)
            elif n < u.golden:  # human transcripts write a ghunnah left out as نننَ (3) against ننننَ (4)
                add(u.word, u.kind, 'khafi', u.golden, n, 'ghunnah_short' if u.kind == 'ghunnah' else 'idgham_ghunnah_short')
        elif u.kind in ('shadda', 'idgham'):
            n, _, _ = _run(heard, max(0, hs - 1), min(len(heard), he + 1), u.char)
            if u.kind == 'idgham' and more_nun(u, hs, he):
                add(u.word, 'idgham', 'khafi', 2, n, 'idgham_missed', letter=u.char)
            elif n == 1:
                add(u.word, 'shadda', 'jali', 2, 1, 'shadda_missing', letter=u.char)

    # whatever the rules did not explain: other letters, other vowels, dropped or added sounds (clear mistakes)
    for tag, i1, i2, j1, j2 in Levenshtein.opcodes(ref.phonemes, heard):
        if tag == 'equal': continue
        exp, got = ref.phonemes[i1:i2], heard[j1:j2]
        if i2 > i1 and all(covered[i1:i2]) and (not got or set(got) <= set(exp) | set(LONG) | {'ڇ', 'ں', '۾', 'ن', 'م'}):
            continue  # a length / ghunnah difference: already judged above
        if tag == 'insert' and any(u.kind == 'madd' and u.s <= i1 <= u.e and set(got) <= {u.char} for u in ref.units):
            continue  # a lin (شَيْءٍ: its ي) held longer: the madd check judged its length
        if ref.riwaya == 'warsh' and tag in ('insert', 'replace') and set(strip_len(got)) <= {'ء'} | HARAKAT and 'ء' in got:
            continue  # a hamza Warsh drops (naql, ibdal) heard anyway: the models learned Hafs first; not judged
        w = next((k for k, (a, z) in enumerate(ref.spans) if a <= i1 < z), len(ref.words) - 1)
        pos[0], span[0] = i1, (j1, j2)
        if i1 < ONSET: continue  # the first sounds of a breath: often clipped or attacked by the recording, not the reciter
        e_core, g_core = strip_len(exp), strip_len(got)
        if e_core == g_core: continue  # only lengths differ
        if unsure(j1, j2, jali_thr): continue
        if tag == 'replace' and len(e_core) == len(g_core) == 1 and e_core in HARAKAT and g_core in HARAKAT:
            L = {'ar': 0, 'en': 1, 'fr': 2}
            notes[w].append({'rule': 'vowel', 'severity': 'jali', 'expected': exp, 'heard': got, 'pos': i1,
                             'msg': {l: _msg('vowel', l, want=VOWEL_NAME[e_core][L[l]], heard=VOWEL_NAME[g_core][L[l]]) for l in langs}})
        elif tag == 'replace':
            add(w, 'letter', 'jali', exp, got, 'letter', want=exp, heard=got)
        elif tag == 'delete':
            if set(exp) <= set(LONG) | HARAKAT and len(exp) == 1: continue  # one vowel sign: within the model's noise
            add(w, 'dropped', 'jali', exp, '', 'dropped', want=exp)
        elif tag == 'insert':
            if i1 == 0 or i1 == len(ref.phonemes): continue  # before the first / after the last word: not this passage
            if set(got) <= set(LONG):
                if len(got) >= 2: add(w, 'madd_added', 'khafi', '', got, 'madd_added')
                continue
            if len(got) == 1 and got in HARAKAT: continue
            add(w, 'added', 'jali', '', got, 'added', heard=got)

    # a word whose sounds are (almost) all missing was skipped
    for k, (a, z) in enumerate(ref.spans):
        if z > a and b[z] - b[a] <= max(0, (z - a) // 4):
            notes[k] = [{'rule': 'word', 'severity': 'jali', 'expected': ref.phonemes[a:z], 'heard': heard[b[a]:b[z]], 'pos': a,
                         'msg': {l: _msg('word_missing', l) for l in langs}}]

    # the same kind of madd must keep the same length through the recitation (munfasil 4 → always 4)
    for rule, seen in madd_seen.items():
        if rule in ('MonfaselMaddRule', 'MottaselMaddRule', 'AaredMaddRule', 'BadalMadd') and len(seen) >= 2:
            lens = [n for _, n in seen if n]
            if lens and max(lens) - min(lens) >= 2:
                w = max(seen, key=lambda x: abs(x[1] - round(sum(lens) / len(lens))))[0]
                notes[w].append({'rule': rule + ':uneven', 'severity': 'khafi', 'expected': 'same', 'heard': lens, 'pos': None,
                                 'msg': {l: _msg('madd_uneven', l, name=name_l(MADD[rule], l), lens=' / '.join(map(str, lens))) for l in langs}})

    if heard_sifat:
        _sifat_notes(ref, heard_sifat, notes, langs)

    idx = ref.index or list(range(len(ref.words)))
    return [{'word': w, 'index': idx[k], 'stop': k in (ref.ends or [])[:-1], 'ok': not any(n['severity'] == 'jali' for n in notes[k]) and not notes[k],
             'notes': notes[k], 'madd': madd_heard[k]} for k, w in enumerate(ref.words)]


def name_l(m, lang):
    return {'ar': m[1], 'en': m[2], 'fr': m[3]}[lang]


def strip_len(s):
    """a sound without its length: runs collapsed, the length marks of madd/ghunnah removed"""
    out = []
    for c in s:
        if out and out[-1] == c: continue
        out.append(c)
    return ''.join(c for c in out if c not in LONG and c not in 'ںڇ۾')


def _sifat_notes(ref, heard_sifat, notes, langs):
    """compare tafkhim / tarqiq, hams / jahr, safir of each sound group with the expected one (groups matched by text)"""
    exp = [(s.phonemes, s) for s in ref.sifat]
    got = [(g[0], g) for g in heard_sifat]
    pos, ends = 0, []
    for p, _ in exp: ends.append((pos, pos + len(p))); pos += len(p)
    gi = 0
    for (p, s), (a, z) in zip(exp, ends):
        while gi < len(got) and got[gi][0] != p and len(got[gi][0]) < 1: gi += 1
        if gi >= len(got): break
        if got[gi][0] != p:
            # look a little ahead for the same group (the model may have split or merged one)
            k = next((x for x in range(gi, min(gi + 3, len(got))) if got[x][0] == p), None)
            if k is None: continue
            gi = k
        g = got[gi][1]; gi += 1
        w = next((k for k, (wa, wz) in enumerate(ref.spans) if wa <= a < wz), None)
        if w is None: continue
        for attr, names in SIFA_NAME.items():
            want, have = getattr(s, attr), g[1 + SIFAT.index(attr)]
            if have and want and have != want and want in names and have in names:
                letter = strip_len(p)[:1] or p[:1]
                if letter not in SIFA_LETTERS: continue
                if {want, have} == {'mofakham', 'low_mofakham'}: continue  # degrees of the same tafkhim
                notes[w].append({'rule': attr, 'severity': 'khafi', 'expected': want, 'heard': have, 'pos': a,
                                 'msg': {l: _msg('sifa', l, letter=letter, want=names[want][0], heard=names[have][0],
                                                 want_en=names[want][1], heard_en=names[have][1],
                                                 want_fr=names[want][2], heard_fr=names[have][2]) for l in langs}})
