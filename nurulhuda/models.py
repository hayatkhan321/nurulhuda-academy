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
