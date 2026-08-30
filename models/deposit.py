from datetime import datetime
from . import db


class Deposit(db.Model):
    __tablename__ = "deposit"

    id = db.Column(db.Integer, primary_key=True)
    mess_id = db.Column(db.Integer, db.ForeignKey("mess.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
