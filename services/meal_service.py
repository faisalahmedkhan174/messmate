from datetime import date
from models import db
from models.meal import Meal
from models.member import Member
from utils.dates import days_in_month, month_date_range

MEAL_TYPES = ["breakfast", "lunch", "dinner"]


class MealService:
    @staticmethod
    def get_month_meal_matrix(mess_id, year, month):
        """Fetch all meal states for the month and structure as meal_map[member_id][day][meal_type] = bool."""
        start, end = month_date_range(year, month)
        meal_rows = (
            Meal.query.filter_by(mess_id=mess_id)
            .filter(Meal.date >= start, Meal.date <= end)
            .all()
        )
        meal_map = {}
        for m in meal_rows:
            meal_map.setdefault(m.member_id, {}).setdefault(m.date.day, {})[m.meal_type] = m.taken
        return meal_map

    @staticmethod
    def toggle_meal(mess_id, member_id, year, month, day, meal_type, taken):
        """Record or update a single meal state for a member on a specific date."""
        if meal_type not in MEAL_TYPES:
            raise ValueError(f"Invalid meal type: {meal_type}")

        member = Member.query.filter_by(id=member_id, mess_id=mess_id).first()
        if not member:
            raise ValueError("Member not found in current mess.")

        try:
            meal_date = date(year, month, day)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date: {year}-{month}-{day}")

        record = Meal.query.filter_by(
            mess_id=mess_id,
            member_id=member.id,
            date=meal_date,
            meal_type=meal_type
        ).first()

        if record:
            record.taken = bool(taken)
        else:
            record = Meal(
                mess_id=mess_id,
                member_id=member.id,
                date=meal_date,
                meal_type=meal_type,
                taken=bool(taken)
            )
            db.session.add(record)

        db.session.commit()
        return bool(record.taken)

    @staticmethod
    def mark_all_for_day(mess_id, year, month, day, meal_types, taken=True):
        """Bulk update meals for all active members on a specific day."""
        active_members = Member.query.filter_by(mess_id=mess_id, status="Active").all()
        try:
            meal_date = date(year, month, day)
        except ValueError:
            raise ValueError("Invalid date.")

        for m in active_members:
            for mt in meal_types:
                if mt not in MEAL_TYPES:
                    continue
                record = Meal.query.filter_by(
                    mess_id=mess_id, member_id=m.id, date=meal_date, meal_type=mt
                ).first()
                if record:
                    record.taken = bool(taken)
                else:
                    db.session.add(Meal(
                        mess_id=mess_id, member_id=m.id, date=meal_date,
                        meal_type=mt, taken=bool(taken)
                    ))
        db.session.commit()
        return True
