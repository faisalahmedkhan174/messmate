from datetime import date
from models import db
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit
from utils.dates import days_in_month, month_date_range
from utils.currency import safe_div, round_currency


class SettlementService:
    @staticmethod
    def get_month_totals(mess_id, year, month):
        """
        Calculate aggregate totals for the month:
        - total_bazar
        - total_meals
        - total_deposits
        - final_rate = safe_div(total_bazar, total_meals)
        """
        start, end = month_date_range(year, month)

        total_bazar = (
            db.session.query(db.func.coalesce(db.func.sum(Bazar.amount), 0.0))
            .filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
            .scalar()
        )
        total_meals = (
            Meal.query.filter(
                Meal.mess_id == mess_id,
                Meal.date >= start,
                Meal.date <= end,
                Meal.taken.is_(True)
            ).count()
        )
        total_deposits = (
            db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0.0))
            .filter(Deposit.mess_id == mess_id, Deposit.date >= start, Deposit.date <= end)
            .scalar()
        )

        final_rate = safe_div(total_bazar, total_meals)

        return {
            "total_bazar": round_currency(total_bazar),
            "total_meals": total_meals,
            "total_deposits": round_currency(total_deposits),
            "final_rate": round_currency(final_rate),
        }

    @staticmethod
    def get_daily_history(mess_id, year, month):
        """
        Return day-by-day running history:
        - date, daily_bazar, cumulative_bazar, daily_meals, cumulative_meals, running_rate
        """
        start, end = month_date_range(year, month)

        bazar_rows = (
            Bazar.query.filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
            .all()
        )
        meal_rows = (
            Meal.query.filter(
                Meal.mess_id == mess_id,
                Meal.date >= start,
                Meal.date <= end,
                Meal.taken.is_(True)
            ).all()
        )

        bazar_by_day = {}
        for b in bazar_rows:
            bazar_by_day[b.date] = bazar_by_day.get(b.date, 0.0) + b.amount

        meals_by_day = {}
        for m in meal_rows:
            meals_by_day[m.date] = meals_by_day.get(m.date, 0) + 1

        history = []
        cum_bazar = 0.0
        cum_meals = 0
        day_count = days_in_month(year, month)

        for day_num in range(1, day_count + 1):
            d = date(year, month, day_num)
            daily_bazar = bazar_by_day.get(d, 0.0)
            daily_meals = meals_by_day.get(d, 0)
            cum_bazar += daily_bazar
            cum_meals += daily_meals
            rate = safe_div(cum_bazar, cum_meals)
            history.append({
                "date": d,
                "daily_bazar": round_currency(daily_bazar),
                "cumulative_bazar": round_currency(cum_bazar),
                "daily_meals": daily_meals,
                "cumulative_meals": cum_meals,
                "running_rate": round_currency(rate),
            })

        return history

    @staticmethod
    def get_member_settlement(mess_id, year, month):
        """
        High-performance per-member settlement calculation.
        Uses batch SQL aggregation in 2 queries instead of 4*N queries,
        eliminating the N+1 query problem while preserving exact financial results.
        """
        start, end = month_date_range(year, month)
        totals = SettlementService.get_month_totals(mess_id, year, month)
        final_rate = totals["final_rate"]

        members = (
            Member.query.filter_by(mess_id=mess_id)
            .order_by(Member.name.asc())
            .all()
        )

        # Batch query 1: Meals grouped by member_id and meal_type
        meal_counts_query = (
            db.session.query(
                Meal.member_id,
                Meal.meal_type,
                db.func.count(Meal.id)
            )
            .filter(
                Meal.mess_id == mess_id,
                Meal.date >= start,
                Meal.date <= end,
                Meal.taken.is_(True)
            )
            .group_by(Meal.member_id, Meal.meal_type)
            .all()
        )
        meal_counts = {}
        for member_id, meal_type, count in meal_counts_query:
            meal_counts.setdefault(member_id, {})[meal_type] = count

        # Batch query 2: Deposits grouped by member_id
        deposit_sums_query = (
            db.session.query(
                Deposit.member_id,
                db.func.sum(Deposit.amount)
            )
            .filter(
                Deposit.mess_id == mess_id,
                Deposit.date >= start,
                Deposit.date <= end
            )
            .group_by(Deposit.member_id)
            .all()
        )
        deposit_sums = {member_id: amt for member_id, amt in deposit_sums_query}

        results = []
        for mem in members:
            mem_meals = meal_counts.get(mem.id, {})
            b_count = mem_meals.get("breakfast", 0)
            l_count = mem_meals.get("lunch", 0)
            d_count = mem_meals.get("dinner", 0)
            total_meals = b_count + l_count + d_count

            meal_cost = round_currency(total_meals * final_rate)
            total_deposit = round_currency(deposit_sums.get(mem.id, 0.0))
            balance = round_currency(total_deposit - meal_cost)

            if balance > 0:
                status = "refund"
            elif balance < 0:
                status = "due"
            else:
                status = "settled"

            results.append({
                "member": mem,
                "breakfast": b_count,
                "lunch": l_count,
                "dinner": d_count,
                "total_meals": total_meals,
                "meal_cost": meal_cost,
                "total_deposit": total_deposit,
                "balance": balance,
                "status": status,
            })

        return results
