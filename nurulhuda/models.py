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
