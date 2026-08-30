from . import db


class Meal(db.Model):
    __tablename__ = "meal"
    __table_args__ = (
        db.UniqueConstraint("mess_id", "member_id", "date", "meal_type",
                             name="uq_meal_mess_member_date_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    mess_id = db.Column(db.Integer, db.ForeignKey("mess.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast / lunch / dinner
    taken = db.Column(db.Boolean, default=False, nullable=False)
