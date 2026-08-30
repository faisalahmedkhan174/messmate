from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class User(db.Model):
    __tablename__ = "user"
    __table_args__ = (
        db.UniqueConstraint("mess_id", "username", name="uq_user_mess_username"),
    )

    id = db.Column(db.Integer, primary_key=True)
    mess_id = db.Column(db.Integer, db.ForeignKey("mess.id"), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    manager_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), default="Manager", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
