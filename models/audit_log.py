from datetime import datetime
from . import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    admin_username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=False)  # Mess, User, System
    target_id = db.Column(db.Integer, nullable=True)
    target_name = db.Column(db.String(150), nullable=True)
    details = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
