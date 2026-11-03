from datetime import datetime
from . import db


class Mess(db.Model):
    __tablename__ = "mess"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    manager_name = db.Column(db.String(150), nullable=False)
    target_meal_rate = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default="Active", nullable=False)  # Active / Suspended
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="mess", cascade="all, delete-orphan")
    members = db.relationship("Member", backref="mess", cascade="all, delete-orphan")
    meals = db.relationship("Meal", backref="mess", cascade="all, delete-orphan")
    bazars = db.relationship("Bazar", backref="mess", cascade="all, delete-orphan")
    deposits = db.relationship("Deposit", backref="mess", cascade="all, delete-orphan")
