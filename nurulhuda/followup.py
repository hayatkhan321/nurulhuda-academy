"""Automatic, polite follow-up e-mails to families who asked for a free trial.

Day 0 (straight away): confirmation (mail.trial_emails).  Day 2, day 5, day 10: the three below.
They stop as soon as the family pays, clicks "stop these e-mails", or the founders mark the request closed.
Written in the language the family used on the site. Run once a day by Vercel (/cron/trial-followups).
"""
import html
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, url_for

from nurulhuda import books, db, mail
from nurulhuda.models import CreditEntry, Family, Invoice, TrialRequest

# Requests made before this feature went live are left alone.
START = datetime(2026, 11, 14, tzinfo=timezone.utc)
DAYS = {1: 2, 2: 5, 3: 10}          # step -> days after the request
MIN_GAP = timedelta(days=2)         # never two reminders closer than this, even if the cron missed days

T = {
    "en": {
        "hello": "Assalamu alaikum {name},",
        "your_child": "your child",
        "s1_new_subject": "A good time for {child}'s free class?",
        "s1_new_body": "We would love to give {child} a free trial class this week. Reply to this e-mail with two or three "
                       "times that suit you, and we will match a teacher to your time zone.",
        "s1_new_button": "Reply with a time",
        "s1_done_subject": "How was {child}'s first class?",
        "s1_done_body": "We hope {child} enjoyed the trial class. If you are happy, choose a plan and classes can start this "
                        "week. A good way to start is 3 days a week.",
        "s2_subject": "What a month at Nurul Huda looks like",
        "s2_body": "Every class is one to one, with the same teacher. After each class you receive a short report: the surah "
                   "and verse, or the Qaida lesson, your child reached, and what to practise. You only pay for classes that "
                   "take place.",
        "s3_subject": "We have kept a place for {child}",
        "s3_body": "This is our last reminder. Whenever you are ready, simply reply to this e-mail and we will arrange a "
                   "teacher for {child}.",
        "plans": "See plans and prices",
        "book": "Book a free trial class",
        "thanks": "JazakAllahu khairan,",
        "stop": "Don't want these e-mails? Stop them here.",
        "c0_subject": "We have your free trial request",
        "c0_body": "Thank you for asking for a free trial class. Within one working day we will contact you to agree a time, "
                   "and match you with a teacher who suits your child's level and your time zone.",
        "c0_reply": "If you have a question in the meantime, simply reply to this e-mail.",
        "page_title": "Stop reminder e-mails",
        "page_ask": "You will not receive any more reminder e-mails about your free trial request.",
        "page_button": "Stop the e-mails",
        "page_done": "Done. We will not send you any more reminders. You can still write to us at any time.",
    },
    "ur": {
        "hello": "السلام علیکم {name}،",
        "your_child": "آپ کے بچے",
        "s1_new_subject": "{child} کی مفت کلاس کے لیے کون سا وقت مناسب ہے؟",
        "s1_new_body": "ہم اس ہفتے {child} کو ایک مفت آزمائشی کلاس دینا چاہیں گے۔ اس ای میل کے جواب میں اپنی سہولت کے دو یا تین "
                       "اوقات لکھ دیجیے، ہم آپ کے ٹائم زون کے مطابق استاد مقرر کر دیں گے۔",
        "s1_new_button": "وقت بتائیں",
        "s1_done_subject": "{child} کی پہلی کلاس کیسی رہی؟",
        "s1_done_body": "امید ہے {child} کو آزمائشی کلاس پسند آئی ہوگی۔ اگر آپ مطمئن ہیں تو ایک پلان منتخب کریں، کلاسیں اسی ہفتے "
                        "شروع ہو سکتی ہیں۔ شروع کرنے کے لیے ہفتے میں 3 دن کا پلان اچھا رہتا ہے۔",
        "s2_subject": "نور الہدیٰ میں ایک مہینہ کیسا ہوتا ہے",
        "s2_body": "ہر کلاس انفرادی ہوتی ہے اور ایک ہی استاد کے ساتھ۔ ہر کلاس کے بعد آپ کو مختصر رپورٹ ملتی ہے: بچہ کس سورت اور آیت، "
                   "یا قاعدے کے کس سبق تک پہنچا، اور کیا مشق کرنی ہے۔ آپ صرف انہی کلاسوں کی ادائیگی کرتے ہیں جو ہوں۔",
        "s3_subject": "ہم نے {child} کے لیے جگہ رکھی ہوئی ہے",
        "s3_body": "یہ ہماری آخری یاد دہانی ہے۔ جب بھی آپ تیار ہوں، بس اس ای میل کا جواب دیں، ہم {child} کے لیے استاد کا انتظام کر دیں گے۔",
        "plans": "پلان اور فیس دیکھیں",
        "book": "مفت آزمائشی کلاس بک کریں",
        "thanks": "جزاک اللہ خیراً،",
        "stop": "یہ ای میلز نہیں چاہیے؟ یہاں بند کریں۔",
        "c0_subject": "آپ کی مفت آزمائشی کلاس کی درخواست موصول ہو گئی",
        "c0_body": "مفت آزمائشی کلاس کی درخواست کا شکریہ۔ ایک کاروباری دن کے اندر ہم آپ سے وقت طے کرنے کے لیے رابطہ کریں گے، اور "
                   "آپ کے بچے کی سطح اور آپ کے ٹائم زون کے مطابق استاد مقرر کریں گے۔",
        "c0_reply": "اس دوران کوئی سوال ہو تو بس اس ای میل کا جواب دیں۔",
        "page_title": "یاد دہانی کی ای میلز بند کریں",
        "page_ask": "آپ کو اپنی مفت کلاس کی درخواست کے بارے میں مزید یاد دہانی کی ای میلز نہیں آئیں گی۔",
        "page_button": "ای میلز بند کریں",
        "page_done": "ہو گیا۔ ہم آپ کو مزید یاد دہانیاں نہیں بھیجیں گے۔ آپ جب چاہیں ہم سے رابطہ کر سکتے ہیں۔",
    },
    "ar": {
        "hello": "السلام عليكم {name}،",
        "your_child": "طفلكم",
        "s1_new_subject": "ما الوقت المناسب لحصة {child} المجانية؟",
        "s1_new_body": "يسعدنا أن نقدم لـ{child} حصة تجريبية مجانية هذا الأسبوع. ردّوا على هذه الرسالة بوقتين أو ثلاثة تناسبكم، "
                       "وسنختار معلمًا يناسب منطقتكم الزمنية.",
        "s1_new_button": "أرسلوا الوقت المناسب",
        "s1_done_subject": "كيف كانت الحصة الأولى لـ{child}؟",
        "s1_done_body": "نرجو أن يكون {child} قد استمتع بالحصة التجريبية. إن كنتم راضين، اختاروا خطة ويمكن أن تبدأ الحصص هذا "
                        "الأسبوع. ومن البدايات الجيدة 3 أيام في الأسبوع.",
        "s2_subject": "كيف يبدو شهر في نور الهدى",
        "s2_body": "كل حصة فردية ومع المعلم نفسه. بعد كل حصة يصلكم تقرير قصير: السورة والآية، أو درس القاعدة، الذي وصل إليه طفلكم، "
                   "وما يحتاج إلى مراجعته. ولا تدفعون إلا عن الحصص التي تُعقد فعلًا.",
        "s3_subject": "حجزنا مكانًا لـ{child}",
        "s3_body": "هذه آخر رسالة تذكير منا. متى كنتم مستعدين، ردّوا على هذه الرسالة وسنرتب معلمًا لـ{child}.",
        "plans": "الخطط والأسعار",
        "book": "احجزوا حصة تجريبية مجانية",
        "thanks": "جزاكم الله خيرًا،",
        "stop": "لا تريدون هذه الرسائل؟ أوقفوها من هنا.",
        "c0_subject": "وصلنا طلب الحصة التجريبية المجانية",
        "c0_body": "شكرًا لطلبكم حصة تجريبية مجانية. خلال يوم عمل واحد سنتواصل معكم لتحديد الوقت، ونختار معلمًا يناسب مستوى "
                   "طفلكم ومنطقتكم الزمنية.",
        "c0_reply": "إن كان لديكم أي سؤال في الأثناء، ردّوا على هذه الرسالة.",
        "page_title": "إيقاف رسائل التذكير",
        "page_ask": "لن تصلكم بعد الآن رسائل تذكير بخصوص طلب الحصة التجريبية المجانية.",
        "page_button": "أوقفوا الرسائل",
        "page_done": "تم. لن نرسل إليكم أي تذكير بعد الآن، ويمكنكم مراسلتنا في أي وقت.",
    },
    "hi": {
        "hello": "अस्सलामु अलैकुम {name},",
        "your_child": "आपके बच्चे",
        "s1_new_subject": "{child} की मुफ़्त क्लास के लिए कौन सा समय ठीक रहेगा?",
        "s1_new_body": "हम इस हफ़्ते {child} को एक मुफ़्त ट्रायल क्लास देना चाहेंगे। इस ई-मेल के जवाब में अपनी सुविधा के दो-तीन समय "
                       "लिख दीजिए, हम आपके टाइम ज़ोन के हिसाब से उस्ताद तय कर देंगे।",
        "s1_new_button": "समय बताएँ",
        "s1_done_subject": "{child} की पहली क्लास कैसी रही?",
        "s1_done_body": "उम्मीद है {child} को ट्रायल क्लास पसंद आई होगी। अगर आप संतुष्ट हैं तो एक प्लान चुनें, क्लासें इसी हफ़्ते "
                        "शुरू हो सकती हैं। शुरुआत के लिए हफ़्ते में 3 दिन का प्लान अच्छा रहता है।",
        "s2_subject": "नूरुल हुदा में एक महीना कैसा होता है",
        "s2_body": "हर क्लास अकेले बच्चे के लिए होती है, एक ही उस्ताद के साथ। हर क्लास के बाद आपको छोटी रिपोर्ट मिलती है: बच्चा किस "
                   "सूरह और आयत, या क़ायदे के किस सबक़ तक पहुँचा, और क्या अभ्यास करना है। आप सिर्फ़ उन्हीं क्लासों का भुगतान "
                   "करते हैं जो होती हैं।",
        "s3_subject": "हमने {child} के लिए जगह रखी है",
        "s3_body": "यह हमारी आख़िरी याद-दिहानी है। जब भी आप तैयार हों, बस इस ई-मेल का जवाब दें, हम {child} के लिए उस्ताद का "
                   "इंतज़ाम कर देंगे।",
        "plans": "प्लान और फ़ीस देखें",
        "book": "मुफ़्त ट्रायल क्लास बुक करें",
        "thanks": "जज़ाकल्लाहु ख़ैरन,",
        "stop": "ये ई-मेल नहीं चाहिए? यहाँ बंद करें।",
        "c0_subject": "आपकी मुफ़्त ट्रायल क्लास की अर्ज़ी मिल गई",
        "c0_body": "मुफ़्त ट्रायल क्लास की अर्ज़ी के लिए शुक्रिया। एक कामकाजी दिन के अंदर हम समय तय करने के लिए आपसे संपर्क करेंगे, "
                   "और आपके बच्चे के स्तर और आपके टाइम ज़ोन के हिसाब से उस्ताद तय करेंगे।",
        "c0_reply": "इस बीच कोई सवाल हो तो बस इस ई-मेल का जवाब दें।",
        "page_title": "याद-दिहानी ई-मेल बंद करें",
        "page_ask": "आपको अपनी मुफ़्त क्लास की अर्ज़ी के बारे में और याद-दिहानी ई-मेल नहीं आएँगे।",
        "page_button": "ई-मेल बंद करें",
        "page_done": "हो गया। हम आपको और याद-दिहानी नहीं भेजेंगे। आप कभी भी हमसे संपर्क कर सकते हैं।",
    },
    "ms": {
        "hello": "Assalamualaikum {name},",
        "your_child": "anak anda",
        "s1_new_subject": "Bilakah masa yang sesuai untuk kelas percuma {child}?",
        "s1_new_body": "Kami ingin memberi {child} satu kelas percubaan percuma minggu ini. Balas e-mel ini dengan dua atau tiga "
                       "masa yang sesuai, dan kami akan memilih guru mengikut zon waktu anda.",
        "s1_new_button": "Balas dengan masa",
        "s1_done_subject": "Bagaimana kelas pertama {child}?",
        "s1_done_body": "Kami harap {child} seronok dengan kelas percubaan itu. Jika anda berpuas hati, pilih pelan dan kelas boleh "
                        "bermula minggu ini. Permulaan yang baik ialah 3 hari seminggu.",
        "s2_subject": "Sebulan di Nurul Huda",
        "s2_body": "Setiap kelas adalah satu lawan satu, dengan guru yang sama. Selepas setiap kelas anda menerima laporan ringkas: "
                   "surah dan ayat, atau pelajaran Qaida, yang dicapai anak anda dan apa yang perlu dilatih. Anda hanya membayar "
                   "kelas yang benar-benar berlangsung.",
        "s3_subject": "Kami telah simpan tempat untuk {child}",
        "s3_body": "Ini peringatan terakhir kami. Bila-bila masa anda bersedia, balas sahaja e-mel ini dan kami akan aturkan guru "
                   "untuk {child}.",
        "plans": "Lihat pelan dan harga",
        "book": "Tempah kelas percubaan percuma",
        "thanks": "Jazakallahu khairan,",
        "stop": "Tidak mahu e-mel ini? Hentikan di sini.",
        "c0_subject": "Permohonan kelas percubaan percuma anda telah diterima",
        "c0_body": "Terima kasih kerana memohon kelas percubaan percuma. Dalam satu hari bekerja kami akan menghubungi anda untuk "
                   "menetapkan masa, dan memilih guru yang sesuai dengan tahap anak anda dan zon waktu anda.",
        "c0_reply": "Jika ada soalan sementara itu, balas sahaja e-mel ini.",
        "page_title": "Hentikan e-mel peringatan",
        "page_ask": "Anda tidak akan menerima lagi e-mel peringatan tentang permohonan kelas percubaan percuma anda.",
        "page_button": "Hentikan e-mel",
        "page_done": "Selesai. Kami tidak akan menghantar peringatan lagi. Anda masih boleh menulis kepada kami bila-bila masa.",
    },
    "id": {
        "hello": "Assalamualaikum {name},",
        "your_child": "anak Anda",
        "s1_new_subject": "Kapan waktu yang cocok untuk kelas gratis {child}?",
        "s1_new_body": "Kami ingin memberikan {child} satu kelas percobaan gratis minggu ini. Balas e-mail ini dengan dua atau tiga "
                       "waktu yang cocok, dan kami akan memilih guru sesuai zona waktu Anda.",
        "s1_new_button": "Balas dengan waktu",
        "s1_done_subject": "Bagaimana kelas pertama {child}?",
        "s1_done_body": "Kami harap {child} menikmati kelas percobaannya. Jika Anda puas, pilih paket dan kelas bisa dimulai minggu "
                        "ini. Awal yang baik adalah 3 hari seminggu.",
        "s2_subject": "Seperti apa sebulan di Nurul Huda",
        "s2_body": "Setiap kelas bersifat privat, dengan guru yang sama. Setelah setiap kelas Anda menerima laporan singkat: surah dan "
                   "ayat, atau pelajaran Qaida, yang dicapai anak Anda dan apa yang perlu dilatih. Anda hanya membayar kelas yang "
                   "benar-benar berlangsung.",
        "s3_subject": "Kami menyimpan tempat untuk {child}",
        "s3_body": "Ini pengingat terakhir kami. Kapan pun Anda siap, cukup balas e-mail ini dan kami akan mengatur guru untuk {child}.",
        "plans": "Lihat paket dan harga",
        "book": "Pesan kelas percobaan gratis",
        "thanks": "Jazakallahu khairan,",
        "stop": "Tidak ingin menerima e-mail ini? Hentikan di sini.",
        "c0_subject": "Permintaan kelas percobaan gratis Anda sudah kami terima",
        "c0_body": "Terima kasih telah meminta kelas percobaan gratis. Dalam satu hari kerja kami akan menghubungi Anda untuk "
                   "menyepakati waktu, dan memilih guru yang sesuai dengan tingkat anak Anda dan zona waktu Anda.",
        "c0_reply": "Jika ada pertanyaan sementara itu, cukup balas e-mail ini.",
        "page_title": "Hentikan e-mail pengingat",
        "page_ask": "Anda tidak akan lagi menerima e-mail pengingat tentang permintaan kelas percobaan gratis Anda.",
        "page_button": "Hentikan e-mail",
        "page_done": "Selesai. Kami tidak akan mengirim pengingat lagi. Anda tetap bisa menghubungi kami kapan saja.",
    },
    "es": {
        "hello": "Assalamu alaikum {name}:",
        "your_child": "su hijo o hija",
        "s1_new_subject": "¿Qué horario le viene bien para la clase gratuita de {child}?",
        "s1_new_body": "Nos encantaría dar a {child} una clase de prueba gratuita esta semana. Responda a este correo con dos o tres "
                       "horarios que le vengan bien y le asignaremos un profesor según su zona horaria.",
        "s1_new_button": "Responder con un horario",
        "s1_done_subject": "¿Qué tal fue la primera clase de {child}?",
        "s1_done_body": "Esperamos que {child} haya disfrutado de la clase de prueba. Si está satisfecho, elija un plan y las clases "
                        "pueden empezar esta semana. Una buena forma de empezar son 3 días por semana.",
        "s2_subject": "Así es un mes en Nurul Huda",
        "s2_body": "Cada clase es individual y con el mismo profesor. Después de cada clase recibe un breve informe: la sura y el "
                   "versículo, o la lección de Qaida, que alcanzó su hijo y qué debe practicar. Solo paga las clases que se imparten.",
        "s3_subject": "Hemos guardado un lugar para {child}",
        "s3_body": "Este es nuestro último recordatorio. Cuando quiera, responda a este correo y organizaremos un profesor para {child}.",
        "plans": "Ver planes y precios",
        "book": "Reservar una clase de prueba gratuita",
        "thanks": "JazakAllahu khairan,",
        "stop": "¿No quiere recibir estos correos? Deténgalos aquí.",
        "c0_subject": "Hemos recibido su solicitud de clase de prueba gratuita",
        "c0_body": "Gracias por solicitar una clase de prueba gratuita. En un día hábil nos pondremos en contacto con usted para "
                   "acordar un horario y asignarle un profesor adecuado al nivel de su hijo y a su zona horaria.",
        "c0_reply": "Si tiene alguna pregunta mientras tanto, simplemente responda a este correo.",
        "page_title": "Dejar de recibir recordatorios",
        "page_ask": "No recibirá más correos de recordatorio sobre su solicitud de clase de prueba gratuita.",
        "page_button": "Detener los correos",
        "page_done": "Listo. No le enviaremos más recordatorios. Puede escribirnos cuando quiera.",
    },
    "fr": {
        "hello": "Assalamu alaikum {name},",
        "your_child": "votre enfant",
        "s1_new_subject": "Quel moment vous convient pour le cours gratuit de {child} ?",
        "s1_new_body": "Nous serions heureux d'offrir à {child} un cours d'essai gratuit cette semaine. Répondez à cet e-mail avec "
                       "deux ou trois créneaux qui vous conviennent, et nous choisirons un enseignant selon votre fuseau horaire.",
        "s1_new_button": "Répondre avec un créneau",
        "s1_done_subject": "Comment s'est passé le premier cours de {child} ?",
        "s1_done_body": "Nous espérons que {child} a apprécié le cours d'essai. Si vous êtes satisfait, choisissez une formule et les "
                        "cours peuvent commencer cette semaine. Pour commencer, 3 jours par semaine est un bon rythme.",
        "s2_subject": "Un mois à Nurul Huda, concrètement",
        "s2_body": "Chaque cours est individuel, avec le même enseignant. Après chaque cours, vous recevez un court compte rendu : la "
                   "sourate et le verset, ou la leçon de Qaida, atteints par votre enfant, et ce qu'il doit réviser. Vous ne payez "
                   "que les cours qui ont lieu.",
        "s3_subject": "Nous avons gardé une place pour {child}",
        "s3_body": "Ceci est notre dernier rappel. Dès que vous êtes prêt, répondez simplement à cet e-mail et nous trouverons un "
                   "enseignant pour {child}.",
        "plans": "Voir les formules et les tarifs",
        "book": "Réserver un cours d'essai gratuit",
        "thanks": "JazakAllahu khairan,",
        "stop": "Vous ne souhaitez plus ces e-mails ? Arrêtez-les ici.",
        "c0_subject": "Nous avons bien reçu votre demande de cours d'essai gratuit",
        "c0_body": "Merci d'avoir demandé un cours d'essai gratuit. Sous un jour ouvré, nous vous contacterons pour convenir d'un "
                   "horaire et choisir un enseignant adapté au niveau de votre enfant et à votre fuseau horaire.",
        "c0_reply": "Si vous avez une question d'ici là, répondez simplement à cet e-mail.",
        "page_title": "Arrêter les e-mails de rappel",
        "page_ask": "Vous ne recevrez plus d'e-mails de rappel concernant votre demande de cours d'essai gratuit.",
        "page_button": "Arrêter les e-mails",
        "page_done": "C'est fait. Nous ne vous enverrons plus de rappels. Vous pouvez toujours nous écrire quand vous le souhaitez.",
    },
}
RTL = {"ur", "ar"}


def t(lang: str, key: str, **kw) -> str:
    text = T.get(lang, T["en"]).get(key) or T["en"][key]
    return text.format(**{k: html.escape(str(v)) for k, v in kw.items()})


def lang_of(tr: TrialRequest) -> str:
    return tr.site_lang if tr.site_lang in T else "en"


def _aware(dt):
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def has_paid(email: str) -> bool:
    fam = Family.query.filter(db.func.lower(Family.email) == (email or "").strip().lower()).first()
    if not fam:
        return False
    if CreditEntry.query.filter_by(family_id=fam.id, kind="purchase").first():
        return True
    return Invoice.query.filter_by(family_id=fam.id, status="paid").first() is not None


def trial_arranged(tr: TrialRequest) -> bool:
    return tr.status == "converted" or Family.query.filter(
        db.func.lower(Family.email) == (tr.email or "").strip().lower()).first() is not None


def _abs(endpoint: str, **kw) -> str:
    """Links in e-mails always use the public address, even when the daily job runs on a Vercel host name."""
    return current_app.config["SITE_URL"].rstrip("/") + url_for(endpoint, **kw)


def _button(href: str, label: str) -> str:
    return (f'<p style="margin:24px 0"><a href="{html.escape(href)}" style="background:#0b5d45;color:#fff;'
            f'text-decoration:none;padding:12px 22px;border-radius:24px;display:inline-block"><b>{label}</b></a></p>')


def _stop_link(tr: TrialRequest) -> str:
    if not tr.followup_token:
        tr.followup_token = secrets.token_urlsafe(24)
    return _abs("site.followup_stop", token=tr.followup_token)


def _frame(lang: str, name: str, body: str, stop_url: str | None) -> str:
    d = ' dir="rtl" style="text-align:right"' if lang in RTL else ""
    out = (f"<div{d}><p>{t(lang, 'hello', name=name)}</p>{body}"
           f"<p>{t(lang, 'thanks')}<br>Nurul Huda Academy</p>")
    if stop_url:
        out += (f'<p style="font-size:13px;color:#5c6f68;margin-top:28px">'
                f'<a href="{html.escape(stop_url)}" style="color:#5c6f68">{t(lang, "stop")}</a></p>')
    return out + "</div>"


def confirmation(tr: TrialRequest):
    """Day 0: sent straight after the form, in the family's language."""
    lang = lang_of(tr)
    body = f"<p>{t(lang, 'c0_body')}</p><p>{t(lang, 'c0_reply')}</p>"
    return t(lang, "c0_subject"), _frame(lang, tr.parent_name, body, None)


def build(tr: TrialRequest, step: int):
    """Subject and HTML for reminder `step` (1, 2 or 3)."""
    lang = lang_of(tr)
    child = (tr.student_name or "").strip() or t(lang, "your_child")
    pricing = _abs("site.pricing", lang=lang)
    if step == 1 and not trial_arranged(tr):
        reply = f"mailto:{current_app.config.get('MAIL_REPLY_TO') or 'info@nurulhudaacademy.org'}?subject=Free%20trial%20time"
        subject = t(lang, "s1_new_subject", child=child)
        body = f"<p>{t(lang, 's1_new_body', child=child)}</p>" + _button(reply, t(lang, "s1_new_button"))
    elif step == 1:
        subject = t(lang, "s1_done_subject", child=child)
        body = f"<p>{t(lang, 's1_done_body', child=child)}</p>" + _button(pricing, t(lang, "plans"))
    elif step == 2:
        subject = t(lang, "s2_subject")
        body = f"<p>{t(lang, 's2_body')}</p>" + _button(pricing, t(lang, "plans"))
    else:
        subject = t(lang, "s3_subject", child=child)
        book = _abs("site.trial", lang=lang)
        body = f"<p>{t(lang, 's3_body', child=child)}</p>" + _button(book, t(lang, "book"))
    return subject, _frame(lang, tr.parent_name, body, _stop_link(tr))


def state(tr: TrialRequest) -> str:
    """One line for the Sign-ups page."""
    if tr.followup_stopped_at:
        return f"Follow-ups stopped ({tr.followup_stop_reason or 'stopped'})"
    if (tr.followup_step or 0) >= 3:
        return "Follow-ups finished (3 of 3 sent)"
    if _aware(tr.created_at) < START:
        return ""
    return f"Follow-ups: {tr.followup_step or 0} of 3 sent"


def run(now: datetime | None = None) -> dict:
    """Send every reminder that is due. Safe to run more than once a day."""
    now = now or datetime.now(timezone.utc)
    sent = stopped = 0
    rows = (TrialRequest.query.filter(TrialRequest.created_at >= START, TrialRequest.followup_stopped_at.is_(None),
                                      TrialRequest.followup_step < 3, TrialRequest.status != "closed",
                                      TrialRequest.email.isnot(None)).all())
    for tr in rows:
        if has_paid(tr.email):
            tr.followup_stopped_at, tr.followup_stop_reason = now, "paid"
            stopped += 1
            continue
        step = (tr.followup_step or 0) + 1
        due = _aware(tr.created_at) + timedelta(days=DAYS[step])
        last = _aware(tr.followup_last_at)
        if now < due or (last and now - last < MIN_GAP):
            continue
        subject, body = build(tr, step)
        if mail.send_email(tr.email, subject, body, headers={"List-Unsubscribe": f"<{_stop_link(tr)}>"}):
            tr.followup_step, tr.followup_last_at = step, now
            books.log("trial_followup_sent", "trial_request", tr.id, step=step, lang=lang_of(tr))
            sent += 1
        db.session.commit()
    db.session.commit()
    return {"sent": sent, "stopped": stopped}
