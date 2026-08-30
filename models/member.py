from datetime import date
from . import db


class Member(db.Model):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    mess_id = db.Column(db.Integer, db.ForeignKey("mess.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    joining_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Active", nullable=False)  # Active / Inactive

    meals = db.relationship("Meal", backref="member", cascade="all, delete-orphan")
    bazars = db.relationship("Bazar", backref="member", cascade="all, delete-orphan")
    deposits = db.relationship("Deposit", backref="member", cascade="all, delete-orphan")
