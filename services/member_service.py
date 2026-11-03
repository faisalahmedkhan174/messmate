from datetime import date
from models import db
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit
from utils.dates import parse_date, month_date_range
from utils.currency import round_currency, safe_div


class MemberService:
    @staticmethod
    def get_members(mess_id, search_query=None, status_filter="all"):
        query = Member.query.filter_by(mess_id=mess_id)
        if search_query:
            query = query.filter(Member.name.ilike(f"%{search_query.strip()}%"))
        if status_filter in ("Active", "Inactive"):
            query = query.filter_by(status=status_filter)
        return query.order_by(Member.name.asc()).all()

    @staticmethod
    def get_member(mess_id, member_id):
        return Member.query.filter_by(id=member_id, mess_id=mess_id).first()

    @staticmethod
    def add_member(mess_id, name, phone=None, joining_date=None):
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Member name is required.")
        j_date = parse_date(joining_date, default=date.today())
        clean_phone = (phone or "").strip() or None

        member = Member(
            mess_id=mess_id,
            name=clean_name,
            phone=clean_phone,
            joining_date=j_date,
            status="Active"
        )
        db.session.add(member)
        db.session.commit()
        return member

    @staticmethod
    def update_member(mess_id, member_id, name, phone=None, joining_date=None):
        member = MemberService.get_member(mess_id, member_id)
        if not member:
            return None
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Member name is required.")

        member.name = clean_name
        member.phone = (phone or "").strip() or None
        if joining_date:
            member.joining_date = parse_date(joining_date, default=member.joining_date)
        db.session.commit()
        return member

    @staticmethod
    def toggle_status(mess_id, member_id):
        member = MemberService.get_member(mess_id, member_id)
        if not member:
            return None
        member.status = "Inactive" if member.status == "Active" else "Active"
        db.session.commit()
        return member

    @staticmethod
    def delete_member(mess_id, member_id):
        member = MemberService.get_member(mess_id, member_id)
        if not member:
            return False
        db.session.delete(member)
        db.session.commit()
        return True

    @staticmethod
    def get_member_details(mess_id, member_id, year, month):
        member = MemberService.get_member(mess_id, member_id)
        if not member:
            return None

        start, end = month_date_range(year, month)

        # Meals
        meals = (
            Meal.query.filter_by(mess_id=mess_id, member_id=member.id)
            .filter(Meal.date >= start, Meal.date <= end)
            .order_by(Meal.date.asc())
            .all()
        )
        meal_by_date = {}
        for m in meals:
            meal_by_date.setdefault(m.date, {})[m.meal_type] = m.taken

        daily_meal_history = []
        for d in sorted(meal_by_date.keys()):
            row = meal_by_date[d]
            daily_meal_history.append({
                "date": d,
                "breakfast": row.get("breakfast", False),
                "lunch": row.get("lunch", False),
                "dinner": row.get("dinner", False),
            })

        total_b = sum(1 for m in meals if m.meal_type == "breakfast" and m.taken)
        total_l = sum(1 for m in meals if m.meal_type == "lunch" and m.taken)
        total_d = sum(1 for m in meals if m.meal_type == "dinner" and m.taken)
        total_meals = total_b + total_l + total_d

        # Deposits
        deposits = (
            Deposit.query.filter_by(mess_id=mess_id, member_id=member.id)
            .filter(Deposit.date >= start, Deposit.date <= end)
            .order_by(Deposit.date.asc())
            .all()
        )
        total_deposits = round_currency(sum(d.amount for d in deposits))

        # Bazars
        bazars = (
            Bazar.query.filter_by(mess_id=mess_id, member_id=member.id)
            .filter(Bazar.date >= start, Bazar.date <= end)
            .order_by(Bazar.date.asc())
            .all()
        )
        total_bazar = round_currency(sum(b.amount for b in bazars))

        # Final meal rate for the month
        from services.settlement_service import SettlementService
        totals = SettlementService.get_month_totals(mess_id, year, month)
        final_rate = totals["final_rate"]
        meal_cost = round_currency(total_meals * final_rate)
        balance = round_currency(total_deposits - meal_cost)

        return {
            "member": member,
            "year": year,
            "month": month,
            "total_breakfast": total_b,
            "total_lunch": total_l,
            "total_dinner": total_d,
            "total_meals": total_meals,
            "total_deposits": total_deposits,
            "total_bazar": total_bazar,
            "meal_cost": meal_cost,
            "balance": balance,
            "daily_meal_history": daily_meal_history,
            "deposits": deposits,
            "bazars": bazars,
        }
