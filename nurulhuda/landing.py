"""Search landing pages: one page per thing parents search for (a topic or a country).

Each page is useful on its own: real prices in the local currency, the local time zones, and answers to that
family's questions. Text is written per language here (not through keys.json) because these are long articles.
Only languages listed in "langs" are offered to search engines; other languages see the English page, marked noindex.
Only write what is true of the academy today.
"""

TOPICS = ["female-quran-teacher-online", "noorani-qaida-online", "online-tajweed-classes", "online-hifz-classes"]
COUNTRIES = ["online-quran-classes-uae", "online-quran-classes-qatar", "online-quran-classes-saudi-arabia",
             "online-quran-classes-canada", "online-quran-classes-usa", "online-quran-classes-uk"]

_COMMON_EN = [
    ("How it works", [
        "Book a free trial class. Tell us your child's age, level and the times that suit you, and we reply within "
        "one working day.",
        "We match your child with a tested teacher whose hours fit yours, and keep the same teacher wherever possible.",
        "After every class the teacher records where your child reached and what to practise, so you can follow "
        "progress from your family page.",
        "You pay only for classes that take place: a class the teacher misses, or that you cancel at least 12 hours "
        "before, is not charged.",
    ]),
]

PAGES = {
    # ---------------------------------------------------------------- topics
    "female-quran-teacher-online": {
        "kind": "topic", "course": "qaida", "langs": ["en", "ur", "ar"],
        "text": {
            "en": {
                "nav": "Female Quran teachers",
                "title": "Female Quran Teacher Online for Girls and Mothers",
                "desc": "One-to-one online Quran classes with a female teacher, for girls, mothers and sisters. "
                        "Noorani Qaida, reading, tajweed and hifz. Book a free trial class.",
                "h1": "Online Quran classes with a female teacher",
                "lead": "Many families want their daughters, or mothers themselves, to learn with a woman teacher. "
                        "At Nurul Huda Academy you can ask for a female teacher for every class, from the first "
                        "letters of the Noorani Qaida to tajweed and hifz.",
                "sections": [
                    ("Who teaches", [
                        "Our Head of Academics is a Hafiza, and every teacher passes a recitation test before teaching. "
                        "Female teachers are available for girls, for women, and for younger boys whose parents prefer it.",
                        "Classes are one to one, in our own online classroom, with the Quran page on screen so the "
                        "teacher can point to each word.",
                    ]),
                    ("What she can teach", [
                        "Noorani Qaida for beginners from age 4, fluent reading (nazira), tajweed, hifz with daily "
                        "revision, and Arabic and Islamic studies alongside.",
                        "Explanations can be in English, Urdu or Arabic. Tell us which language your child is most "
                        "comfortable in.",
                    ]),
                ] + _COMMON_EN,
                "faq": [
                    ("Can my son also learn with a female teacher?", "Yes, for younger children many families prefer "
                     "it. Ask when you book the trial."),
                    ("Will it always be the same teacher?", "We keep the same teacher wherever possible. After 6 "
                     "classes you can keep her or try another teacher of the same standard, at no charge."),
                ],
            },
            "ur": {
                "title": "خواتین قرآن ٹیچر آن لائن: بچیوں اور خواتین کے لیے",
                "desc": "خاتون استانی کے ساتھ انفرادی آن لائن قرآن کلاسیں، بچیوں، ماؤں اور بہنوں کے لیے۔ نورانی قاعدہ، ناظرہ، تجوید اور حفظ۔ مفت آزمائشی کلاس بک کریں۔",
                "h1": "خاتون استانی کے ساتھ آن لائن قرآن کلاسیں",
                "lead": "بہت سے خاندان چاہتے ہیں کہ ان کی بیٹیاں، یا مائیں خود، کسی خاتون استانی سے پڑھیں۔ نور الہدیٰ اکیڈمی میں آپ ہر کلاس کے لیے خاتون استانی مانگ سکتے ہیں، نورانی قاعدے کے پہلے حروف سے لے کر تجوید اور حفظ تک۔",
                "sections": [
                    ("کون پڑھاتا ہے", [
                        "ہماری ہیڈ آف اکیڈمکس حافظہ ہیں، اور ہر استاد پڑھانے سے پہلے تلاوت کا امتحان پاس کرتا ہے۔ خاتون استانیاں بچیوں، خواتین اور ان چھوٹے بچوں کے لیے دستیاب ہیں جن کے والدین یہ پسند کریں۔",
                        "کلاسیں انفرادی ہوتی ہیں، ہمارے اپنے آن لائن کلاس روم میں، اور قرآن کا صفحہ اسکرین پر ہوتا ہے تاکہ استانی ہر لفظ کی نشاندہی کر سکیں۔",
                    ]),
                    ("وہ کیا پڑھا سکتی ہیں", [
                        "4 سال کی عمر سے نورانی قاعدہ، روانی سے ناظرہ، تجوید، روزانہ دہرائی کے ساتھ حفظ، اور ساتھ میں عربی اور اسلامیات۔",
                        "وضاحت انگریزی، اردو یا عربی میں ہو سکتی ہے۔ بتائیں کہ آپ کا بچہ کس زبان میں زیادہ آسانی محسوس کرتا ہے۔",
                    ]),
                    ("طریقہ کار", [
                        "مفت آزمائشی کلاس بک کریں۔ اپنے بچے کی عمر، سطح اور مناسب اوقات بتائیں، ہم ایک کاروباری دن کے اندر جواب دیتے ہیں۔",
                        "ہم آپ کے بچے کے لیے جانچا پرکھا استاد مقرر کرتے ہیں جس کے اوقات آپ کے مطابق ہوں، اور جہاں تک ممکن ہو وہی استاد رکھتے ہیں۔",
                        "ہر کلاس کے بعد استاد لکھتے ہیں کہ بچہ کہاں تک پہنچا اور کیا مشق کرنی ہے، تاکہ آپ اپنے فیملی پیج پر پیش رفت دیکھ سکیں۔",
                        "آپ صرف انہی کلاسوں کی ادائیگی کرتے ہیں جو ہوں: جو کلاس استاد چھوڑ دے، یا آپ 12 گھنٹے پہلے منسوخ کر دیں، اس کا چارج نہیں ہوتا۔",
                    ]),
                ],
                "faq": [
                    ("کیا میرا بیٹا بھی خاتون استانی سے پڑھ سکتا ہے؟", "جی ہاں، چھوٹے بچوں کے لیے بہت سے خاندان یہی پسند کرتے ہیں۔ آزمائشی کلاس بک کرتے وقت بتا دیں۔"),
                    ("کیا ہمیشہ وہی استانی ہوں گی؟", "جہاں تک ممکن ہو ہم وہی استاد رکھتے ہیں۔ 6 کلاسوں کے بعد آپ انہیں رکھ سکتے ہیں یا اسی معیار کی کسی اور استانی کو آزما سکتے ہیں، بغیر کسی فیس کے۔"),
                ],
            },
            "ar": {
                "title": "معلمة قرآن أونلاين للبنات والأمهات",
                "desc": "حصص قرآن فردية أونلاين مع معلمة، للبنات والأمهات والأخوات. القاعدة النورانية والقراءة والتجويد والتحفيظ. احجزوا حصة تجريبية مجانية.",
                "h1": "حصص قرآن أونلاين مع معلمة",
                "lead": "كثير من العائلات تريد أن تتعلم بناتها، أو الأمهات أنفسهن، مع معلمة. في أكاديمية نور الهدى يمكنكم طلب معلمة لكل الحصص، من أول حروف القاعدة النورانية إلى التجويد والتحفيظ.",
                "sections": [
                    ("من يُدرّس", [
                        "رئيسة الشؤون الأكاديمية لدينا حافظة لكتاب الله، وكل معلم يجتاز اختبار تلاوة قبل أن يبدأ التدريس. المعلمات متاحات للبنات والنساء وللأولاد الصغار إذا فضّل الأهل ذلك.",
                        "الحصص فردية في فصلنا الإلكتروني الخاص، وصفحة المصحف أمام الطالب على الشاشة لتشير المعلمة إلى كل كلمة.",
                    ]),
                    ("ماذا تُدرّس", [
                        "القاعدة النورانية للمبتدئين من عمر 4 سنوات، والقراءة المتقنة من المصحف، والتجويد، والتحفيظ مع المراجعة اليومية، إلى جانب العربية والدراسات الإسلامية.",
                        "يمكن أن يكون الشرح بالعربية أو الإنجليزية أو الأردية. أخبرونا باللغة الأسهل لطفلكم.",
                    ]),
                    ("كيف نعمل", [
                        "احجزوا حصة تجريبية مجانية. أخبرونا بعمر طفلكم ومستواه والأوقات المناسبة، وسنرد خلال يوم عمل واحد.",
                        "نختار لطفلكم معلمًا مختبَرًا تناسب ساعاته أوقاتكم، ونحافظ على المعلم نفسه قدر الإمكان.",
                        "بعد كل حصة يسجل المعلم أين وصل طفلكم وما يحتاج إلى مراجعته، فتتابعون التقدم من صفحة العائلة.",
                        "لا تدفعون إلا عن الحصص التي تُعقد: الحصة التي يتغيب عنها المعلم، أو التي تلغونها قبل 12 ساعة على الأقل، لا تُحتسب.",
                    ]),
                ],
                "faq": [
                    ("هل يمكن لابني أن يتعلم مع معلمة أيضًا؟", "نعم، كثير من العائلات تفضّل ذلك للأطفال الصغار. اذكروا ذلك عند حجز الحصة التجريبية."),
                    ("هل ستكون المعلمة نفسها دائمًا؟", "نحافظ على المعلم نفسه قدر الإمكان. بعد 6 حصص يمكنكم الإبقاء عليها أو تجربة معلمة أخرى بالمستوى نفسه دون أي رسوم."),
                ],
            },
        },
    },
    "noorani-qaida-online": {
        "kind": "topic", "course": "qaida", "langs": ["en", "ur", "ar"],
        "text": {
            "en": {
                "nav": "Noorani Qaida online",
                "title": "Noorani Qaida Online Classes for Beginners",
                "desc": "Learn the Noorani Qaida online, one to one with a tested teacher. For children from age 4 "
                        "and adult beginners. Free Qaida PDF and a free trial class.",
                "h1": "Noorani Qaida online, one to one",
                "lead": "The Noorani Qaida is where reading the Quran begins: the Arabic letters, their shapes and "
                        "sounds, then joining them into words. With a patient teacher and short daily classes, most "
                        "children move from the first letters to reading words within a few months.",
                "sections": [
                    ("What your child learns", [
                        "The 17 lessons of the Qaida step by step: single letters and their correct sounds (makharij), "
                        "joined letters, short vowels, tanween, long vowels, sukoon and shaddah, and then reading "
                        "words from the Quran.",
                        "After every class the teacher records the lesson reached, for example \"lesson 8 of 17\", "
                        "so you always know how far your child has come.",
                    ]),
                    ("Who it is for", [
                        "Children from age 4, older children starting late, and adults who never had the chance to "
                        "learn. Classes are 30 minutes, which suits young children's attention.",
                        "You can download the Noorani Qaida free from our Resources page to practise between classes.",
                    ]),
                ] + _COMMON_EN,
                "faq": [
                    ("How long does the Qaida take?", "It depends on the child and how many classes a week. With 3 to "
                     "5 classes a week, children typically finish in 4 to 8 months."),
                    ("Do I need to buy a book?", "No. The teacher shows the pages on screen, and you can download the "
                     "Qaida free from our Resources page."),
                ],
            },
            "ur": {
                "title": "نورانی قاعدہ آن لائن کلاسیں، ابتدائی طلبہ کے لیے",
                "desc": "جانچے پرکھے استاد کے ساتھ انفرادی طور پر نورانی قاعدہ آن لائن سیکھیں۔ 4 سال سے بچوں اور بڑوں کے لیے۔ مفت قاعدہ پی ڈی ایف اور مفت آزمائشی کلاس۔",
                "h1": "نورانی قاعدہ آن لائن، انفرادی کلاس",
                "lead": "قرآن پڑھنے کا آغاز نورانی قاعدے سے ہوتا ہے: عربی حروف، ان کی شکلیں اور آوازیں، پھر انہیں جوڑ کر الفاظ بنانا۔ صبر والے استاد اور مختصر روزانہ کلاسوں کے ساتھ اکثر بچے چند مہینوں میں پہلے حروف سے الفاظ پڑھنے تک پہنچ جاتے ہیں۔",
                "sections": [
                    ("آپ کا بچہ کیا سیکھتا ہے", [
                        "قاعدے کے 17 اسباق قدم بہ قدم: الگ الگ حروف اور ان کے درست مخارج، مرکب حروف، حرکات، تنوین، مد، سکون اور تشدید، پھر قرآن کے الفاظ پڑھنا۔",
                        "ہر کلاس کے بعد استاد لکھتے ہیں کہ کون سا سبق ہوا، مثلاً \"17 میں سے سبق 8\"، تاکہ آپ کو ہمیشہ معلوم رہے کہ بچہ کہاں تک پہنچا۔",
                    ]),
                    ("یہ کس کے لیے ہے", [
                        "4 سال سے بچے، دیر سے شروع کرنے والے بڑے بچے، اور وہ بالغ جنہیں سیکھنے کا موقع نہیں ملا۔ کلاس 30 منٹ کی ہوتی ہے جو چھوٹے بچوں کے لیے موزوں ہے۔",
                        "کلاسوں کے درمیان مشق کے لیے نورانی قاعدہ ہمارے ریسورسز پیج سے مفت ڈاؤن لوڈ کر سکتے ہیں۔",
                    ]),
                    ("طریقہ کار", [
                        "مفت آزمائشی کلاس بک کریں۔ اپنے بچے کی عمر، سطح اور مناسب اوقات بتائیں، ہم ایک کاروباری دن کے اندر جواب دیتے ہیں۔",
                        "ہم آپ کے بچے کے لیے جانچا پرکھا استاد مقرر کرتے ہیں جس کے اوقات آپ کے مطابق ہوں، اور جہاں تک ممکن ہو وہی استاد رکھتے ہیں۔",
                        "آپ صرف انہی کلاسوں کی ادائیگی کرتے ہیں جو ہوں: جو کلاس استاد چھوڑ دے، یا آپ 12 گھنٹے پہلے منسوخ کر دیں، اس کا چارج نہیں ہوتا۔",
                    ]),
                ],
                "faq": [
                    ("قاعدہ کتنے عرصے میں مکمل ہوتا ہے؟", "یہ بچے اور ہفتے کی کلاسوں پر منحصر ہے۔ ہفتے میں 3 سے 5 کلاسوں کے ساتھ بہت سے بچے 4 سے 8 مہینوں میں مکمل کر لیتے ہیں۔"),
                    ("کیا کتاب خریدنی ہوگی؟", "نہیں۔ استاد صفحات اسکرین پر دکھاتے ہیں، اور قاعدہ ہمارے ریسورسز پیج سے مفت ڈاؤن لوڈ ہو سکتا ہے۔"),
                ],
            },
            "ar": {
                "title": "دروس القاعدة النورانية أونلاين للمبتدئين",
                "desc": "تعلّموا القاعدة النورانية أونلاين في حصص فردية مع معلم مختبَر. للأطفال من عمر 4 سنوات وللكبار المبتدئين. ملف القاعدة مجانًا وحصة تجريبية مجانية.",
                "h1": "القاعدة النورانية أونلاين، حصص فردية",
                "lead": "القاعدة النورانية هي بداية قراءة القرآن: الحروف العربية وأشكالها وأصواتها، ثم وصلها لتكوين الكلمات. مع معلم صبور وحصص يومية قصيرة، ينتقل أكثر الأطفال من أول الحروف إلى قراءة الكلمات خلال بضعة أشهر.",
                "sections": [
                    ("ماذا يتعلم طفلكم", [
                        "دروس القاعدة السبعة عشر خطوة بخطوة: الحروف المفردة ومخارجها الصحيحة، والحروف المركبة، والحركات، والتنوين، والمدود، والسكون والشدة، ثم قراءة كلمات من القرآن.",
                        "بعد كل حصة يسجل المعلم الدرس الذي وصل إليه الطفل، مثل \"الدرس 8 من 17\"، فتعرفون دائمًا مقدار تقدمه.",
                    ]),
                    ("لمن هذه الدروس", [
                        "للأطفال من عمر 4 سنوات، وللأطفال الأكبر الذين بدأوا متأخرين، وللكبار الذين لم تتح لهم الفرصة. الحصة 30 دقيقة، وهي مناسبة لتركيز الصغار.",
                        "يمكنكم تحميل القاعدة النورانية مجانًا من صفحة المصادر للتدرب بين الحصص.",
                    ]),
                    ("كيف نعمل", [
                        "احجزوا حصة تجريبية مجانية. أخبرونا بعمر طفلكم ومستواه والأوقات المناسبة، وسنرد خلال يوم عمل واحد.",
                        "نختار لطفلكم معلمًا مختبَرًا تناسب ساعاته أوقاتكم، ونحافظ على المعلم نفسه قدر الإمكان.",
                        "لا تدفعون إلا عن الحصص التي تُعقد: الحصة التي يتغيب عنها المعلم، أو التي تلغونها قبل 12 ساعة على الأقل، لا تُحتسب.",
                    ]),
                ],
                "faq": [
                    ("كم تستغرق القاعدة؟", "يعتمد ذلك على الطفل وعدد الحصص في الأسبوع. مع 3 إلى 5 حصص أسبوعيًا يُنهيها كثير من الأطفال في 4 إلى 8 أشهر."),
                    ("هل نحتاج إلى شراء كتاب؟", "لا. يعرض المعلم الصفحات على الشاشة، ويمكنكم تحميل القاعدة مجانًا من صفحة المصادر."),
                ],
            },
        },
    },
    "online-tajweed-classes": {
        "kind": "topic", "course": "tajweed", "langs": ["en", "ur", "ar"],
        "text": {
            "en": {
                "nav": "Tajweed classes",
                "title": "Online Tajweed Classes for Kids and Adults",
                "desc": "One-to-one online tajweed classes: makharij, ghunnah, madd and more, practised aloud with "
                        "a tested teacher. Free trial class.",
                "h1": "Online tajweed classes, one to one",
                "lead": "Tajweed is reciting the Quran as it was revealed: each letter from its right place, with its "
                        "right qualities and lengths. It is learned by listening and reciting, so every class is spent "
                        "reading aloud with the teacher, who corrects as you go.",
                "sections": [
                    ("What the course covers", [
                        "The exit points of the letters (makharij) and their qualities (sifat), noon and meem sakinah "
                        "(ikhfa, idgham, iqlab, izhar), ghunnah, the types of madd, qalqalah, and stopping and starting "
                        "correctly.",
                        "Rules are taught through the verses your child is reading, not as a list to memorise. The teacher "
                        "notes what was practised after each class, for example \"working on ikhfa and madd\".",
                    ]),
                    ("Who it is for", [
                        "Children who already read the Quran fluently, and adults who want to correct their recitation. "
                        "If your child is still on the Qaida, start there first.",
                    ]),
                ] + _COMMON_EN,
                "faq": [
                    ("My child reads already. Do they need tajweed?", "If your child reads fluently, tajweed is the next "
                     "step: it makes the recitation correct and beautiful. The trial class shows where to start."),
                    ("Are classes in English?", "Explanations can be in English, Urdu or Arabic, as you prefer."),
                ],
            },
            "ur": {
                "title": "بچوں اور بڑوں کے لیے آن لائن تجوید کلاسیں",
                "desc": "انفرادی آن لائن تجوید کلاسیں: مخارج، غنہ، مد اور مزید، جانچے پرکھے استاد کے ساتھ بلند آواز میں مشق۔ مفت آزمائشی کلاس۔",
                "h1": "آن لائن تجوید کلاسیں، انفرادی",
                "lead": "تجوید قرآن کو اسی طرح پڑھنا ہے جیسے نازل ہوا: ہر حرف اپنے صحیح مخرج سے، اپنی صفات اور مد کے ساتھ۔ یہ سن کر اور پڑھ کر سیکھی جاتی ہے، اس لیے ہر کلاس استاد کے ساتھ بلند آواز میں پڑھنے میں گزرتی ہے، اور استاد ساتھ ساتھ درستی کرتے ہیں۔",
                "sections": [
                    ("کورس میں کیا شامل ہے", [
                        "حروف کے مخارج اور صفات، نون ساکن اور میم ساکن کے احکام (اخفاء، ادغام، اقلاب، اظہار)، غنہ، مد کی اقسام، قلقلہ، اور وقف و ابتدا۔",
                        "قواعد انہی آیات کے ذریعے سکھائے جاتے ہیں جو بچہ پڑھ رہا ہے، رٹنے کی فہرست کے طور پر نہیں۔ ہر کلاس کے بعد استاد لکھتے ہیں کہ کیا مشق ہوئی، مثلاً \"اخفاء اور مد پر کام\"۔",
                    ]),
                    ("یہ کس کے لیے ہے", [
                        "وہ بچے جو قرآن روانی سے پڑھتے ہیں، اور وہ بالغ جو اپنی تلاوت درست کرنا چاہتے ہیں۔ اگر آپ کا بچہ ابھی قاعدہ پڑھ رہا ہے تو پہلے وہاں سے شروع کریں۔",
                    ]),
                    ("طریقہ کار", [
                        "مفت آزمائشی کلاس بک کریں۔ اپنے بچے کی عمر، سطح اور مناسب اوقات بتائیں، ہم ایک کاروباری دن کے اندر جواب دیتے ہیں۔",
                        "آپ صرف انہی کلاسوں کی ادائیگی کرتے ہیں جو ہوں: جو کلاس استاد چھوڑ دے، یا آپ 12 گھنٹے پہلے منسوخ کر دیں، اس کا چارج نہیں ہوتا۔",
                    ]),
                ],
                "faq": [
                    ("میرا بچہ پڑھ لیتا ہے، کیا اسے تجوید کی ضرورت ہے؟", "اگر بچہ روانی سے پڑھتا ہے تو تجوید اگلا قدم ہے: اس سے تلاوت درست اور خوبصورت ہوتی ہے۔ آزمائشی کلاس سے پتا چل جاتا ہے کہ کہاں سے شروع کرنا ہے۔"),
                    ("کیا کلاسیں اردو میں ہو سکتی ہیں؟", "جی ہاں، وضاحت اردو، انگریزی یا عربی میں ہو سکتی ہے، جیسے آپ چاہیں۔"),
                ],
            },
            "ar": {
                "title": "دروس تجويد أونلاين للأطفال والكبار",
                "desc": "حصص تجويد فردية أونلاين: المخارج والغنة والمدود وغيرها، بالتطبيق الصوتي مع معلم مختبَر. حصة تجريبية مجانية.",
                "h1": "دروس تجويد أونلاين، حصص فردية",
                "lead": "التجويد هو تلاوة القرآن كما أُنزل: كل حرف من مخرجه بصفاته ومقاديره. ويُتعلَّم بالسماع والتلاوة، لذلك تمضي كل حصة في القراءة بصوت مسموع مع المعلم الذي يصحح أولًا بأول.",
                "sections": [
                    ("محتوى الدورة", [
                        "مخارج الحروف وصفاتها، وأحكام النون الساكنة والتنوين والميم الساكنة (الإخفاء والإدغام والإقلاب والإظهار)، والغنة، وأنواع المدود، والقلقلة، والوقف والابتداء.",
                        "تُشرح الأحكام من خلال الآيات التي يقرؤها الطالب، لا كقائمة للحفظ. ويسجل المعلم بعد كل حصة ما تم التدرب عليه، مثل \"العمل على الإخفاء والمد\".",
                    ]),
                    ("لمن هذه الدروس", [
                        "للأطفال الذين يقرؤون القرآن بطلاقة، وللكبار الذين يريدون تصحيح تلاوتهم. إن كان طفلكم ما زال في القاعدة فليبدأ بها أولًا.",
                    ]),
                    ("كيف نعمل", [
                        "احجزوا حصة تجريبية مجانية. أخبرونا بعمر طفلكم ومستواه والأوقات المناسبة، وسنرد خلال يوم عمل واحد.",
                        "لا تدفعون إلا عن الحصص التي تُعقد: الحصة التي يتغيب عنها المعلم، أو التي تلغونها قبل 12 ساعة على الأقل، لا تُحتسب.",
                    ]),
                ],
                "faq": [
                    ("طفلي يقرأ، فهل يحتاج إلى التجويد؟", "إن كان يقرأ بطلاقة فالتجويد هو الخطوة التالية: يجعل التلاوة صحيحة وجميلة. والحصة التجريبية تبيّن من أين يبدأ."),
                    ("هل يمكن أن يكون الشرح بالعربية؟", "نعم، يمكن أن يكون الشرح بالعربية أو الإنجليزية أو الأردية كما تفضلون."),
                ],
            },
        },
    },
    "online-hifz-classes": {
        "kind": "topic", "course": "hifz", "langs": ["en", "ur", "ar"],
        "text": {
            "en": {
                "nav": "Online hifz classes",
                "title": "Online Hifz Classes for Kids: Memorise the Quran",
                "desc": "Online hifz programme for children: one-to-one daily classes with new lessons (sabaq) and "
                        "revision (muraja'ah), and progress you can see. Free trial class.",
                "h1": "Online hifz classes for children",
                "lead": "Memorising the Quran is a long, blessed journey, and steady daily practice matters more than "
                        "speed. Our hifz plan gives your child a teacher who listens every day, sets the next portion, "
                        "and makes sure what was learned is not forgotten.",
                "sections": [
                    ("How a hifz class works", [
                        "Each class has three parts: reciting the new lesson (sabaq) prepared at home, the recent lessons "
                        "(sabqi), and older revision (manzil or muraja'ah). The teacher listens, corrects and sets the "
                        "next portion.",
                        "Hifz classes are 60 minutes, 5 days a week. After every class the teacher records the surah and "
                        "verse reached, and your family page shows how much of the Quran your child has covered.",
                    ]),
                    ("Who it is for", [
                        "Children who read the Quran fluently with good tajweed and are ready for a daily commitment, "
                        "with a parent who can help them revise at home. The trial class helps decide if your child is ready.",
                    ]),
                ] + _COMMON_EN,
                "faq": [
                    ("How long does hifz take?", "Every child is different. With daily classes and home revision, "
                     "memorising the whole Quran usually takes several years; many families set a goal of one juz at a time."),
                    ("Can my child do hifz alongside school?", "Yes. Classes can be after school or early in the morning, "
                     "so hifz fits alongside school."),
                ],
            },
            "ur": {
                "title": "بچوں کے لیے آن لائن حفظ کلاسیں",
                "desc": "بچوں کے لیے آن لائن حفظ پروگرام: نئے سبق اور دہرائی کے ساتھ روزانہ انفرادی کلاسیں، اور پیش رفت جو آپ دیکھ سکیں۔ مفت آزمائشی کلاس۔",
                "h1": "بچوں کے لیے آن لائن حفظ کلاسیں",
                "lead": "قرآن حفظ کرنا ایک طویل اور بابرکت سفر ہے، اور اس میں رفتار سے زیادہ روزانہ کی پابندی اہم ہے۔ ہمارے حفظ پلان میں آپ کے بچے کو ایسا استاد ملتا ہے جو روزانہ سنتا ہے، اگلا حصہ دیتا ہے، اور یقینی بناتا ہے کہ یاد کیا ہوا بھولے نہیں۔",
                "sections": [
                    ("حفظ کی کلاس کیسے ہوتی ہے", [
                        "ہر کلاس کے تین حصے ہوتے ہیں: گھر پر تیار کیا گیا نیا سبق، سبقی (حالیہ اسباق)، اور منزل (پرانی دہرائی)۔ استاد سنتے ہیں، درستی کرتے ہیں اور اگلا حصہ دیتے ہیں۔",
                        "حفظ کی کلاسیں 60 منٹ کی، ہفتے میں 5 دن ہوتی ہیں۔ ہر کلاس کے بعد استاد سورت اور آیت لکھتے ہیں، اور فیملی پیج پر نظر آتا ہے کہ بچے نے قرآن کا کتنا حصہ مکمل کیا۔",
                    ]),
                    ("یہ کس کے لیے ہے", [
                        "وہ بچے جو اچھی تجوید کے ساتھ روانی سے قرآن پڑھتے ہیں اور روزانہ کی پابندی کے لیے تیار ہیں، اور جن کے والدین گھر پر دہرائی میں مدد کر سکیں۔ آزمائشی کلاس سے فیصلہ کرنے میں مدد ملتی ہے کہ بچہ تیار ہے یا نہیں۔",
                    ]),
                    ("طریقہ کار", [
                        "مفت آزمائشی کلاس بک کریں۔ اپنے بچے کی عمر، سطح اور مناسب اوقات بتائیں، ہم ایک کاروباری دن کے اندر جواب دیتے ہیں۔",
                        "آپ صرف انہی کلاسوں کی ادائیگی کرتے ہیں جو ہوں: جو کلاس استاد چھوڑ دے، یا آپ 12 گھنٹے پہلے منسوخ کر دیں، اس کا چارج نہیں ہوتا۔",
                    ]),
                ],
                "faq": [
                    ("حفظ میں کتنا وقت لگتا ہے؟", "ہر بچہ مختلف ہوتا ہے۔ روزانہ کلاسوں اور گھر پر دہرائی کے ساتھ پورا قرآن حفظ کرنے میں عموماً کئی سال لگتے ہیں؛ بہت سے خاندان ایک وقت میں ایک پارے کا ہدف رکھتے ہیں۔"),
                    ("کیا بچہ اسکول کے ساتھ حفظ کر سکتا ہے؟", "جی ہاں۔ کلاسیں اسکول کے بعد یا صبح سویرے ہو سکتی ہیں، اس لیے حفظ اسکول کے ساتھ ساتھ ہو سکتا ہے۔"),
                ],
            },
            "ar": {
                "title": "حلقات تحفيظ القرآن أونلاين للأطفال",
                "desc": "برنامج تحفيظ أونلاين للأطفال: حصص فردية يومية للسبق الجديد والمراجعة، وتقدّم يمكنكم متابعته. حصة تجريبية مجانية.",
                "h1": "تحفيظ القرآن أونلاين للأطفال",
                "lead": "حفظ القرآن رحلة طويلة مباركة، والمداومة اليومية أهم من السرعة. في برنامج التحفيظ لدينا يحظى طفلكم بمعلم يستمع إليه كل يوم، ويحدد المقطع التالي، ويحرص على ألا يُنسى ما حُفظ.",
                "sections": [
                    ("كيف تسير حصة التحفيظ", [
                        "لكل حصة ثلاثة أجزاء: تسميع السبق الجديد الذي أعدّه الطالب في البيت، والسبقي (الدروس القريبة)، والمنزل (المراجعة القديمة). يستمع المعلم ويصحح ويحدد المقطع التالي.",
                        "حصص التحفيظ مدتها 60 دقيقة، 5 أيام في الأسبوع. بعد كل حصة يسجل المعلم السورة والآية، وتُظهر صفحة العائلة مقدار ما أتمه طفلكم من القرآن.",
                    ]),
                    ("لمن هذا البرنامج", [
                        "للأطفال الذين يقرؤون القرآن بطلاقة وبتجويد جيد ومستعدون للالتزام اليومي، مع أحد الوالدين يساعدهم على المراجعة في البيت. والحصة التجريبية تساعد على معرفة جاهزية الطفل.",
                    ]),
                    ("كيف نعمل", [
                        "احجزوا حصة تجريبية مجانية. أخبرونا بعمر طفلكم ومستواه والأوقات المناسبة، وسنرد خلال يوم عمل واحد.",
                        "لا تدفعون إلا عن الحصص التي تُعقد: الحصة التي يتغيب عنها المعلم، أو التي تلغونها قبل 12 ساعة على الأقل، لا تُحتسب.",
                    ]),
                ],
                "faq": [
                    ("كم يستغرق الحفظ؟", "كل طفل مختلف. مع الحصص اليومية والمراجعة في البيت يستغرق حفظ القرآن كاملًا عادةً عدة سنوات، وكثير من العائلات تضع هدف جزء واحد في كل مرة."),
                    ("هل يمكن الجمع بين التحفيظ والمدرسة؟", "نعم. يمكن أن تكون الحصص بعد الدوام أو في الصباح الباكر، فيجتمع التحفيظ مع المدرسة."),
                ],
            },
        },
    },
    # ---------------------------------------------------------------- countries
    "online-quran-classes-uae": {
        "kind": "country", "currency": "AED", "langs": ["en"],
        "zones": [("Asia/Dubai", "UAE time (GST)")],
        "text": {"en": {
            "nav": "Quran classes in the UAE",
            "title": "Online Quran Classes for Kids in the UAE",
            "desc": "One-to-one online Quran classes for children in Dubai, Sharjah, Abu Dhabi and across the UAE. "
                    "Prices in dirhams, female teachers on request, free trial class.",
            "h1": "Online Quran classes for children in the UAE",
            "lead": "For families in Dubai, Sharjah, Abu Dhabi, Ajman and across the Emirates: one-to-one Quran "
                    "classes at home, at times that fit around school, homework and activities.",
            "sections": [
                ("Times that fit a UAE school day", [
                    "Popular times for UAE families are after school, between 3 pm and 8 pm UAE time, or on Saturday and "
                    "Sunday mornings. Tell us your times and we match a teacher whose hours fit.",
                    "In Ramadan many families move classes to after iftar or before suhoor. Just let us know and we "
                    "adjust the timetable.",
                ]),
                ("Teachers and languages", [
                    "Every teacher passes a recitation test, and female teachers are available on request. Explanations "
                    "can be in English, Arabic or Urdu, so children from Arabic-speaking and South Asian families alike "
                    "feel at home.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Can I pay in dirhams?", "Yes. Our prices for UAE families are in AED, and the ways to pay are listed on our Prices page."),
                ("Do you teach Arabic too?", "Yes. Alongside the Quran we teach Quranic and conversational Arabic and "
                 "Islamic studies."),
            ],
        }},
    },
    "online-quran-classes-qatar": {
        "kind": "country", "currency": "USD", "langs": ["en"],
        "zones": [("Asia/Qatar", "Qatar time (AST)")],
        "text": {"en": {
            "nav": "Quran classes in Qatar",
            "title": "Online Quran Classes for Kids in Qatar",
            "desc": "One-to-one online Quran, tajweed and hifz classes for children in Doha and across Qatar. "
                    "Tested teachers, female teachers on request, free trial class.",
            "h1": "Online Quran classes for children in Qatar",
            "lead": "For families in Doha, Al Rayyan, Al Wakrah and across Qatar: one-to-one Quran classes at home "
                    "with a tested teacher, after school or at the weekend.",
            "sections": [
                ("Times that work in Qatar", [
                    "Popular times in Qatar are after school, between 3 pm and 8 pm Qatar time, or on "
                    "Friday and Saturday. Tell us the times that suit you and we match a teacher whose hours fit.",
                    "In Ramadan we can move classes to after iftar or before suhoor.",
                ]),
                ("Teachers and languages", [
                    "Female teachers are available on request. Explanations can be in Arabic, English or Urdu.",
                    "Prices for Qatar are shown in US dollars; you can also ask to pay in dirhams.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Which currency do I pay in?", "Prices are shown in US dollars, and the ways to pay are listed on our Prices page."),
                ("Can my child memorise the Quran online?", "Yes. Our hifz plan has 60-minute classes 5 days a week "
                 "with daily revision."),
            ],
        }},
    },
    "online-quran-classes-saudi-arabia": {
        "kind": "country", "currency": "USD", "langs": ["en"],
        "zones": [("Asia/Riyadh", "Saudi time (AST)")],
        "text": {"en": {
            "nav": "Quran classes in Saudi Arabia",
            "title": "Online Quran Classes for Kids in Saudi Arabia",
            "desc": "One-to-one online Quran classes for expat children in Riyadh, Jeddah, Dammam and across Saudi "
                    "Arabia. Explanations in English or Urdu. Free trial class.",
            "h1": "Online Quran classes for children in Saudi Arabia",
            "lead": "For expatriate families in Riyadh, Jeddah, Dammam, Khobar and across the Kingdom who want their "
                    "children taught in English or Urdu: one-to-one Quran classes at home with a tested teacher.",
            "sections": [
                ("Times that work in Saudi Arabia", [
                    "Popular times are after school, between 3 pm and 9 pm Saudi time, or on Friday and "
                    "Saturday. Tell us your times and we match a teacher whose hours fit.",
                ]),
                ("Why families choose us", [
                    "Many expat children find Arabic-medium classes hard to follow. Our teachers can explain in English "
                    "or Urdu while the recitation itself is taught with correct Arabic makharij.",
                    "Female teachers are available on request. Prices are shown in US dollars.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Can the teacher explain in Urdu?", "Yes. Choose English, Urdu or Arabic when you book the trial."),
                ("Which currency do I pay in?", "Prices are shown in US dollars, and the ways to pay are listed on our Prices page."),
            ],
        }},
    },
    "online-quran-classes-canada": {
        "kind": "country", "currency": "CAD", "langs": ["en"],
        "zones": [("America/Toronto", "Eastern"), ("America/Winnipeg", "Central"), ("America/Edmonton", "Mountain"),
                  ("America/Vancouver", "Pacific")],
        "text": {"en": {
            "nav": "Quran classes in Canada",
            "title": "Online Quran Classes for Kids in Canada",
            "desc": "One-to-one online Quran classes for children in Toronto, Mississauga, Calgary, Edmonton, Vancouver "
                    "and across Canada. Prices in CAD, evening and weekend times.",
            "h1": "Online Quran classes for children in Canada",
            "lead": "For families in Toronto, Mississauga, Brampton, Ottawa, Montreal, Calgary, Edmonton, Vancouver and "
                    "everywhere in between: one-to-one Quran classes at home, in the evenings or at the weekend.",
            "sections": [
                ("Times across Canada's time zones", [
                    "We schedule every class in your own time zone, Eastern, Central, Mountain or Pacific, and show it "
                    "on your family page in your local time. Weekday evenings after school and weekend mornings "
                    "are the most popular times.",
                    "When the clocks change in March and November, your class stays at the same local time. Tell us "
                    "if anything needs to move.",
                ]),
                ("Teachers and languages", [
                    "Teachers explain in English, so children who grew up in Canada follow easily, or in Urdu or Arabic "
                    "if you prefer. Female teachers are available on request.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Can I pay in Canadian dollars?", "Yes. Our prices for Canada are in CAD, and the ways to pay are listed on our Prices page."),
                ("What if my child is busy with school activities?", "Choose the plan that fits, from 2 days a week to "
                 "daily, and cancel a class at least 12 hours before at no charge."),
            ],
        }},
    },
    "online-quran-classes-usa": {
        "kind": "country", "currency": "USD", "langs": ["en"],
        "zones": [("America/New_York", "Eastern"), ("America/Chicago", "Central"), ("America/Denver", "Mountain"),
                  ("America/Los_Angeles", "Pacific")],
        "text": {"en": {
            "nav": "Quran classes in the USA",
            "title": "Online Quran Classes for Kids in the USA",
            "desc": "One-to-one online Quran, tajweed and hifz classes for children across the United States. "
                    "Evening and weekend times in your time zone, prices in USD.",
            "h1": "Online Quran classes for children in the USA",
            "lead": "For families in New York, New Jersey, Chicago, Houston, Dallas, the Bay Area and across the "
                    "United States: one-to-one Quran classes at home, after school or at the weekend.",
            "sections": [
                ("Times across US time zones", [
                    "Every class is booked in your own time zone, Eastern, Central, Mountain or Pacific, and shown on "
                    "your family page in local time. Weekday evenings and weekend mornings are the most popular times.",
                    "When daylight saving starts or ends, your class stays at the same local time.",
                ]),
                ("Teachers and languages", [
                    "Teachers explain in English, so American-born children follow easily, or in Urdu or Arabic if you "
                    "prefer. Female teachers are available on request.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Can I pay in US dollars?", "Yes. Prices are in USD, and the ways to pay are listed on our Prices page."),
                ("Is there a discount for siblings?", "Yes: 10% off the second child and 15% off the third child and "
                 "every child after."),
            ],
        }},
    },
    "online-quran-classes-uk": {
        "kind": "country", "currency": "GBP", "langs": ["en"],
        "zones": [("Europe/London", "UK time")],
        "text": {"en": {
            "nav": "Quran classes in the UK",
            "title": "Online Quran Classes for Kids in the UK",
            "desc": "One-to-one online Quran classes for children in London, Birmingham, Manchester, Bradford and "
                    "across the UK. Prices in pounds, after-school times, free trial class.",
            "h1": "Online Quran classes for children in the UK",
            "lead": "For families in London, Birmingham, Manchester, Bradford, Leicester, Glasgow and across the UK: "
                    "one-to-one Quran classes at home, so your child learns without the evening trip to the mosque.",
            "sections": [
                ("Times that fit a UK school day", [
                    "Popular times for UK families are after school, between 4 pm and 8 pm UK time, or on Saturday and "
                    "Sunday mornings. Tell us your times and we match a teacher whose hours fit.",
                    "When the clocks change in March and October, your class stays at the same UK time.",
                ]),
                ("Teachers and languages", [
                    "Teachers explain in English, or in Urdu or Arabic if you prefer. Female teachers are available on "
                    "request, and every teacher passes a recitation test.",
                ]),
            ] + _COMMON_EN,
            "faq": [
                ("Can I pay in pounds?", "Yes. Prices for UK families are in GBP, and the ways to pay are listed on our Prices page."),
                ("Is one-to-one better than a mosque class?", "In a one-to-one class the teacher hears every line your "
                 "child reads and corrects it straight away, and you see a report after every class."),
            ],
        }},
    },
}


LABELS = {
    "en": {"faq": "Questions families ask", "related": "Also see", "zones": "We schedule classes in your time zone"},
    "ur": {"faq": "والدین کے عام سوالات", "related": "یہ بھی دیکھیں", "zones": "ہم کلاسیں آپ کے ٹائم زون میں رکھتے ہیں"},
    "ar": {"faq": "أسئلة يطرحها الأهالي", "related": "انظر أيضًا", "zones": "نحدد الحصص بتوقيتكم المحلي"},
}


def text(page: dict, lang: str) -> dict:
    return page["text"].get(lang) or page["text"]["en"]


def nav_links():
    """(slug, English label) for the footer: topics first, then countries."""
    return [(slug, PAGES[slug]["text"]["en"]["nav"]) for slug in TOPICS + COUNTRIES]
