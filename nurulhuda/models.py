from datetime import datetime, timezone

from nurulhuda import db


def _now():
    return datetime.now(timezone.utc)


class TrialRequest(db.Model):
    """A family asking for a free trial class."""
    __tablename__ = "trial_requests"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    parent_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200))                                    # may be empty for WhatsApp requests
    phone = db.Column(db.String(40))
    country = db.Column(db.String(60))
    city = db.Column(db.String(80))
    student_name = db.Column(db.String(120))
    student_age = db.Column(db.String(20))
    course = db.Column(db.String(60))
    teacher_gender = db.Column(db.String(20))
    preferred_times = db.Column(db.String(200))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="new", nullable=False)
    instruction_language = db.Column(db.String(40))
    teacher_pref = db.Column(db.String(10))                             # same / open
    language_profile = db.Column(db.Text)                               # e.g. "Urdu (Native); English (Fluent)"
    english_level = db.Column(db.String(20))
    urdu_level = db.Column(db.String(20))
    site_lang = db.Column(db.String(5))                                 # language the visitor used the site in
    # automatic follow-up e-mails (see followup.py)
    followup_step = db.Column(db.Integer, default=0, nullable=False)    # reminders sent so far (0-3)
    followup_last_at = db.Column(db.DateTime(timezone=True))
    followup_stopped_at = db.Column(db.DateTime(timezone=True))
    followup_stop_reason = db.Column(db.String(20))                     # paid / family / admin
    followup_token = db.Column(db.String(40), unique=True)              # for the "stop these e-mails" link
    source = db.Column(db.String(20), default="website")                # website / whatsapp


class TeacherApplication(db.Model):
    """A teacher applying to teach on the platform."""
    __tablename__ = "teacher_applications"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(40))
    country = db.Column(db.String(60))
    gender = db.Column(db.String(20))
    levels = db.Column(db.String(200))
    qualifications = db.Column(db.Text)
    experience_years = db.Column(db.String(20))
    languages = db.Column(db.String(120))
    hours = db.Column(db.String(200))
    recitation_link = db.Column(db.String(300))
    status = db.Column(db.String(20), default="new", nullable=False)
    language_profile = db.Column(db.Text)                               # e.g. "Urdu (Native); English (Fluent)"
    english_level = db.Column(db.String(20))
    urdu_level = db.Column(db.String(20))
    arabic_level = db.Column(db.String(20))
    site_lang = db.Column(db.String(5))
    uploads = db.relationship("Upload", lazy="select", order_by="Upload.id",
                              primaryjoin="TeacherApplication.id == Upload.application_id")


class DawahRequest(db.Model):
    """Someone who wants to learn about Islam, or a new Muslim asking for classes."""
    __tablename__ = "dawah_requests"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(40))
    country = db.Column(db.String(60))
    interest = db.Column(db.String(80))
    teacher_gender = db.Column(db.String(20))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="new", nullable=False)
    site_lang = db.Column(db.String(5))


# --- Academy operations: families, teachers, classes, credits and teacher pay -------------------
class Family(db.Model):
    """A parent account. Logs in by e-mail link."""
    __tablename__ = "families"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    parent_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    phone = db.Column(db.String(40))
    country = db.Column(db.String(60))
    timezone = db.Column(db.String(60), default="America/Toronto", nullable=False)
    teacher_gender = db.Column(db.String(20))
    recording_consent = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text)
    instruction_language = db.Column(db.String(40))
    site_lang = db.Column(db.String(5), default="en")
    # "same": keep the same teacher where possible; "open": happy to try teachers of the same standard
    teacher_pref = db.Column(db.String(10), default="same")
    membership = db.Column(db.String(10), default="standard", nullable=False)   # standard / gold / diamond (memberships.py)
    membership_since = db.Column(db.DateTime(timezone=True))
    students = db.relationship("Student", backref="family", lazy=True, order_by="Student.id")


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.String(20))
    course = db.Column(db.String(60))
    level = db.Column(db.String(120))
    active = db.Column(db.Boolean, default=True, nullable=False)
    lesson_format = db.Column(db.String(10), default="academic", nullable=False)   # academic (30) / combined (20 + 10 Islamic)


class Teacher(db.Model):
    """An approved teacher. Logs in by e-mail link. Only active teachers can be given classes."""
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    phone = db.Column(db.String(40))
    country = db.Column(db.String(60))
    timezone = db.Column(db.String(60), default="Asia/Karachi", nullable=False)
    gender = db.Column(db.String(20))
    levels = db.Column(db.String(200))
    rate = db.Column(db.Numeric(10, 2), default=0, nullable=False)      # pay per class
    rate_currency = db.Column(db.String(3), default="USD", nullable=False)
    payout_method = db.Column(db.String(200))                           # e.g. "Wise: name / IBAN" or "Payoneer: e-mail"
    active = db.Column(db.Boolean, default=False, nullable=False)
    language_profile = db.Column(db.Text)                               # e.g. "Urdu (Native); English (Fluent)"
    english_level = db.Column(db.String(20))
    urdu_level = db.Column(db.String(20))
    arabic_level = db.Column(db.String(20))
    site_lang = db.Column(db.String(5), default="en")
    application_id = db.Column(db.Integer, db.ForeignKey("teacher_applications.id"))
    conduct_version = db.Column(db.String(20))                          # Code of Conduct version accepted (content.CONDUCT_VERSION)
    conduct_accepted_at = db.Column(db.DateTime(timezone=True))
    tier = db.Column(db.String(10), default="standard", nullable=False)  # standard / gold / diamond teacher (memberships.py)
    qualifications_verified = db.Column(db.Boolean, default=False, nullable=False)
    experience_years = db.Column(db.Integer)
    english_verified = db.Column(db.Boolean, default=False, nullable=False)   # an admin heard the teacher speak it
    urdu_verified = db.Column(db.Boolean, default=False, nullable=False)
    arabic_verified = db.Column(db.Boolean, default=False, nullable=False)
    lang_note = db.Column(db.String(200))


class Package(db.Model):
    """What families buy: a number of classes for a price. Edited by the founders."""
    __tablename__ = "packages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    classes = db.Column(db.Integer, nullable=False)
    minutes = db.Column(db.Integer, default=30, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    # The same plan is sold in several currencies; `plan` ties those rows together (e.g. "3-days").
    plan = db.Column(db.String(40))
    blurb = db.Column(db.String(200))                                   # e.g. "3 days a week, 4 weeks"
    sort = db.Column(db.Integer, default=0, nullable=False)
    public = db.Column(db.Boolean, default=True, nullable=False)        # shown on the public price list


class PromoCode(db.Model):
    """A discount code: the founding-family offer, a mosque partner, a referral or a community rate."""
    __tablename__ = "promo_codes"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    code = db.Column(db.String(30), nullable=False, unique=True)
    percent = db.Column(db.Numeric(5, 2), nullable=False)
    kind = db.Column(db.String(20), default="offer", nullable=False)   # offer / partner / referral / community
    # A community or hardship rate may go past the usual discount cap (never below the floor price).
    beyond_cap = db.Column(db.Boolean, default=False, nullable=False)
    expires_on = db.Column(db.Date)
    max_uses = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True, nullable=False)
    note = db.Column(db.String(200))
    tiers = db.Column(db.String(40))                                    # e.g. "gold,diamond"; empty = every membership


class ClassReview(db.Model):
    """The family's rating of one class, given after it ends."""
    __tablename__ = "class_reviews"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, unique=True)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    stars = db.Column(db.Integer, nullable=False)              # 1 to 5
    comment = db.Column(db.String(1000))
    teacher = db.relationship("Teacher", lazy="joined")
    student = db.relationship("Student", lazy="joined")


class TeacherCheckin(db.Model):
    """After a student's sixth class with a teacher, the family says whether to keep the teacher or try another."""
    __tablename__ = "teacher_checkins"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    choice = db.Column(db.String(10), nullable=False)          # keep / change
    note = db.Column(db.String(500))
    handled = db.Column(db.Boolean, default=False, nullable=False)
    teacher = db.relationship("Teacher", lazy="joined")
    student = db.relationship("Student", lazy="joined")


class Invoice(db.Model):
    """What a family has been asked to pay. Classes are added only when the academy confirms the money arrived."""
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    number = db.Column(db.String(20), nullable=False, unique=True)     # NH-260001, also the payment reference
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    currency = db.Column(db.String(3), nullable=False)
    months = db.Column(db.Integer, default=1, nullable=False)
    classes = db.Column(db.Integer, nullable=False)                     # added to the balance when paid
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    promo_code = db.Column(db.String(30))
    lines = db.Column(db.Text, nullable=False)                          # JSON: one line per child
    # pending (not paid yet) / reported (family says they paid) / paid / cancelled
    status = db.Column(db.String(12), default="pending", nullable=False)
    tier = db.Column(db.String(10), default="standard", nullable=False)   # membership bought with this invoice
    method = db.Column(db.String(20))                                   # paypal / wise / bank / card / cash
    payer_reference = db.Column(db.String(200))
    reported_at = db.Column(db.DateTime(timezone=True))
    paid_at = db.Column(db.DateTime(timezone=True))
    amount_received = db.Column(db.Numeric(10, 2))
    admin_note = db.Column(db.String(300))
    family = db.relationship("Family", lazy="joined")


class CreditEntry(db.Model):
    """Every change to a family's class balance. The balance is the sum of `classes`."""
    __tablename__ = "credit_entries"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    classes = db.Column(db.Integer, nullable=False)                     # +10 bought, -1 used, +1 returned
    kind = db.Column(db.String(20), nullable=False)                     # purchase / used / returned / adjustment / refund
    amount = db.Column(db.Numeric(10, 2))                               # money received (purchases) or refunded
    currency = db.Column(db.String(3))
    method = db.Column(db.String(40))                                   # bank transfer, cash, stripe ...
    reference = db.Column(db.String(200))
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"))
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"))
    note = db.Column(db.String(300))
    receipt_no = db.Column(db.String(20), unique=True)                  # RC-2026-0001 for payments, RF-... for refunds
    aed_rate = db.Column(db.Numeric(14, 6))                             # 1 unit of `currency` in AED, on the day
    amount_aed = db.Column(db.Numeric(12, 2))
    reverses_id = db.Column(db.Integer, db.ForeignKey("credit_entries.id"))   # a correction points at what it corrects
    family_obj = db.relationship("Family", lazy="joined", foreign_keys=[family_id])


class ClassSession(db.Model):
    __tablename__ = "class_sessions"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)   # stored in UTC
    minutes = db.Column(db.Integer, default=30, nullable=False)
    # scheduled / completed / student_missed / teacher_missed / cancelled
    status = db.Column(db.String(20), default="scheduled", nullable=False)
    teacher_note = db.Column(db.Text)
    room_name = db.Column(db.String(80), unique=True)
    teacher_joined_at = db.Column(db.DateTime(timezone=True))
    student_joined_at = db.Column(db.DateTime(timezone=True))
    flagged_at = db.Column(db.DateTime(timezone=True))
    flag_reason = db.Column(db.Text)
    flag_resolution = db.Column(db.String(200))
    # Progress, written by the teacher when marking the class (shown on the family's dashboard).
    prog_book = db.Column(db.String(10))        # "qaida" or "quran"
    prog_surah = db.Column(db.Integer)          # where the class stopped (Quran)
    prog_verse = db.Column(db.Integer)
    prog_lesson = db.Column(db.Integer)         # where the class stopped (Qaida lesson number)
    prog_focus = db.Column(db.String(120))      # what the student is working on, e.g. "ikhfa, madd"
    # Presence, counted in seconds from the classroom every 30 seconds (t_ = teacher, s_ = student's device).
    t_secs = db.Column(db.Integer, default=0, nullable=False)        # in the call
    t_view_secs = db.Column(db.Integer, default=0, nullable=False)   # class window in view (not another tab or app)
    t_cam_secs = db.Column(db.Integer, default=0, nullable=False)    # camera on
    t_marks = db.Column(db.Integer, default=0, nullable=False)       # marks made on the lesson board
    t_beat_at = db.Column(db.DateTime(timezone=True))
    s_secs = db.Column(db.Integer, default=0, nullable=False)
    s_view_secs = db.Column(db.Integer, default=0, nullable=False)
    s_cam_secs = db.Column(db.Integer, default=0, nullable=False)
    s_beat_at = db.Column(db.DateTime(timezone=True))
    student = db.relationship("Student", lazy="joined")
    teacher = db.relationship("Teacher", lazy="joined")


class Homework(db.Model):
    """What the teacher asks the child to practise until the next class, set when marking a class."""
    __tablename__ = "homework"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    task = db.Column(db.String(300), nullable=False)
    minutes = db.Column(db.Integer)                 # minutes a day, optional
    book = db.Column(db.String(10))                 # "quran" / "qaida" / None
    surah = db.Column(db.Integer)
    verse_from = db.Column(db.Integer)
    verse_to = db.Column(db.Integer)
    lesson = db.Column(db.Integer)
    days = db.Column(db.Text, default="", nullable=False)   # dates the family ticked "we practised", YYYY-MM-DD, comma-separated
    teacher = db.relationship("Teacher", lazy="joined")


class Mistake(db.Model):
    """A word the teacher marked on the lesson board. Stays open until the teacher marks it corrected."""
    __tablename__ = "mistakes"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)       # first marked in
    last_class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False)              # last marked in
    surah = db.Column(db.Integer, nullable=False)
    ayah = db.Column(db.Integer, nullable=False)
    word = db.Column(db.Integer, nullable=False)        # word number in the verse, from 1
    text = db.Column(db.String(80), nullable=False)     # the word as shown on the board (King Fahd Hafs text)
    kind = db.Column(db.String(10), nullable=False)     # word / tajweed / harakah
    times = db.Column(db.Integer, default=1, nullable=False)
    fixed_at = db.Column(db.DateTime(timezone=True))
    fixed_class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"))


class TeacherEarning(db.Model):
    """What the academy owes a teacher for one class. Paid in weekly payouts."""
    __tablename__ = "teacher_earnings"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    status = db.Column(db.String(10), default="owed", nullable=False)   # owed / held / paid / void
    payout_id = db.Column(db.Integer, db.ForeignKey("payouts.id"))


class Payout(db.Model):
    __tablename__ = "payouts"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    method = db.Column(db.String(40))
    reference = db.Column(db.String(200))
    voucher_no = db.Column(db.String(20), unique=True)                  # PV-2026-0001
    aed_rate = db.Column(db.Numeric(14, 6))
    amount_aed = db.Column(db.Numeric(12, 2))


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(500), nullable=False)


class LoginToken(db.Model):
    """One-time e-mail sign-in links for families and teachers."""
    __tablename__ = "login_tokens"
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    role = db.Column(db.String(10), nullable=False)                     # family / teacher
    user_id = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))


class Upload(db.Model):
    """A file sent with a teacher application (certificates or CV). Kept in the database, at most 2 MB each."""
    __tablename__ = "uploads"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey("teacher_applications.id"), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)                     # certificate / cv
    filename = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    data = db.deferred(db.Column(db.LargeBinary, nullable=False))   # only loaded when the file is downloaded


class Expense(db.Model):
    """Money the academy spends (video, hosting, licence, salaries ...). Never edited: a mistake is reversed."""
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    spent_on = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    payee = db.Column(db.String(120))
    amount = db.Column(db.Numeric(12, 2), nullable=False)               # negative for a reversal
    currency = db.Column(db.String(3), nullable=False)
    aed_rate = db.Column(db.Numeric(14, 6), nullable=False)
    amount_aed = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(40))
    reference = db.Column(db.String(200))
    voucher_no = db.Column(db.String(20), unique=True, nullable=False)  # EX-2026-0001
    reverses_id = db.Column(db.Integer, db.ForeignKey("expenses.id"))


class AuditLog(db.Model):
    """Who did what, and when. Rows are only ever added."""
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False, index=True)
    actor = db.Column(db.String(40), nullable=False)                    # admin / teacher:3 / family:7 / system
    ip = db.Column(db.String(64))
    action = db.Column(db.String(60), nullable=False)
    entity = db.Column(db.String(40))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)                                        # JSON


class WaContact(db.Model):
    """Someone who messaged the academy's WhatsApp number (see whatsapp.py)."""
    __tablename__ = "wa_contacts"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    wa_id = db.Column(db.String(20), nullable=False, unique=True)       # phone number in international form, no +
    profile_name = db.Column(db.String(120))
    lang = db.Column(db.String(5))
    status = db.Column(db.String(10), default="bot", nullable=False)   # bot / human / muted
    human_since = db.Column(db.DateTime(timezone=True))
    lead_json = db.Column(db.Text)
    trial_request_id = db.Column(db.Integer, db.ForeignKey("trial_requests.id"))
    last_at = db.Column(db.DateTime(timezone=True), default=_now)


class WaMessage(db.Model):
    __tablename__ = "wa_messages"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey("wa_contacts.id"), nullable=False, index=True)
    direction = db.Column(db.String(6), nullable=False)                 # in / bot / staff
    body = db.Column(db.Text, nullable=False)
    wa_message_id = db.Column(db.String(120), unique=True)


class PracticeCheck(db.Model):
    """One staff test of the automatic recitation check (recite.py). No audio is kept: only what the model heard and
    what it said, so the Head of Academics can judge how often it is right for children and adults, boys and girls."""
    __tablename__ = "practice_checks"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))    # empty when an admin ran it
    reader = db.Column(db.String(6), nullable=False)                   # child / adult
    gender = db.Column(db.String(6), nullable=False)                   # male / female
    strictness = db.Column(db.String(10), nullable=False)              # gentle / standard
    surah = db.Column(db.Integer, nullable=False)
    ayah = db.Column(db.Integer, nullable=False)
    seconds = db.Column(db.Float)
    heard = db.Column(db.Text)                                          # the model's phonetic script
    result = db.Column(db.Text)                                         # JSON: one entry per word
    flagged = db.Column(db.Integer, default=0, nullable=False)          # words the check marked
    review = db.Column(db.Text)                                         # JSON: {word index: "right" / "wrong" / "missed"}
    review_note = db.Column(db.String(500))
    reviewed_at = db.Column(db.DateTime(timezone=True))


class ClassroomEvent(db.Model):
    """What happened in a class, as times only (never sound or video): microphone or camera off and back on, a raised
    hand, a lost connection, joining and leaving. classroom.py decides what is reportable."""
    __tablename__ = "classroom_events"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)                     # teacher / student
    person = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(10), nullable=False)                     # mic / camera / hand / network / join / leave
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ended_at = db.Column(db.DateTime(timezone=True))
    seconds = db.Column(db.Integer)
    cause = db.Column(db.String(20))                                    # user / device / network / left / unknown
    announced = db.Column(db.Boolean, default=False, nullable=False)    # a hand was raised just before


class ConductReport(db.Model):
    """A parent's concern about a teacher's behaviour (e.g. personal questions), and how the academy handled it."""
    __tablename__ = "conduct_reports"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class_sessions.id"))
    category = db.Column(db.String(20), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(12), default="open", nullable=False)  # open / looking / upheld / not_upheld
    admin_notes = db.Column(db.Text)
    closed_at = db.Column(db.DateTime(timezone=True))
    family = db.relationship("Family")
    teacher = db.relationship("Teacher")


class SupportApplication(db.Model):
    """A family asking for sponsored lessons for a child. Private: never shown to sponsors or teachers."""
    __tablename__ = "support_applications"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    lessons_asked = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default="pending", nullable=False)  # pending / approved / rejected / closed
    lessons_approved = db.Column(db.Integer, default=0, nullable=False)
    share = db.Column(db.Integer, default=100, nullable=False)           # % of each lesson sponsored (100 = free)
    admin_note = db.Column(db.String(500))
    decided_at = db.Column(db.DateTime(timezone=True))
    family = db.relationship("Family")
    student = db.relationship("Student")


class SponsorPurchase(db.Model):
    """A member buying sponsored lessons (coins), paid like an invoice. One coin = one 30-minute lesson."""
    __tablename__ = "sponsor_purchases"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    number = db.Column(db.String(20), nullable=False, unique=True)       # SP-123456, the payment reference
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
    coins = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(12), default="pending", nullable=False)  # pending / reported / paid / cancelled
    method = db.Column(db.String(20))
    payer_reference = db.Column(db.String(200))
    reported_at = db.Column(db.DateTime(timezone=True))
    paid_at = db.Column(db.DateTime(timezone=True))
    amount_received = db.Column(db.Numeric(10, 2))
    credit_entry_id = db.Column(db.Integer, db.ForeignKey("credit_entries.id"))   # the receipt in the books
    family = db.relationship("Family")


class SponsorEntry(db.Model):
    """The sponsorship wallet, kept apart from class credits. Coins in: purchase / promo; coins out: allocate (to an
    approved application); corrections: refund / adjust. Never edited; mistakes are corrected with a new entry."""
    __tablename__ = "sponsor_entries"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey("families.id"), index=True)         # the sponsor
    coins = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(12), nullable=False)
    purchase_id = db.Column(db.Integer, db.ForeignKey("sponsor_purchases.id"))
    application_id = db.Column(db.Integer, db.ForeignKey("support_applications.id"), index=True)
    note = db.Column(db.String(300))
