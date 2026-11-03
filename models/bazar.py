from datetime import datetime
from . import db


class Bazar(db.Model):
    __tablename__ = "bazar"

    id = db.Column(db.Integer, primary_key=True)
    mess_id = db.Column(db.Integer, db.ForeignKey("mess.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    items_description = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(50), default="Groceries", nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
