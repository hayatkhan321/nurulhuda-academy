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
    email = db.Column(db.String(200), nullable=False)
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
