import calendar
from datetime import date
from functools import wraps

from flask import session, redirect, url_for, flash

from models import db
from models.mess import Mess
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit

MEAL_TYPES = ["breakfast", "lunch", "dinner"]


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("mess_id") or not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)
    return wrapped


def current_mess():
    """Always fetch the mess strictly by the server-side session id."""
    mess_id = session.get("mess_id")
    if not mess_id:
        return None
    return Mess.query.get(mess_id)


def days_in_month(year, month):
    """Correctly handles leap years via Python's calendar module."""
    return calendar.monthrange(year, month)[1]


def month_date_range(year, month):
    last_day = days_in_month(year, month)
    return date(year, month, 1), date(year, month, last_day)


def safe_div(numerator, denominator):
    if not denominator:
        return 0.0
    return numerator / denominator


def get_daily_history(mess_id, year, month):
    """Return list of dicts: date, daily_bazar, cumulative_bazar,
    daily_meals, cumulative_meals, running_rate -- for every day of the month
    up to today (or full month if a past month)."""
    start, end = month_date_range(year, month)

    bazar_rows = (
        Bazar.query.filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
        .all()
    )
    meal_rows = (
        Meal.query.filter(Meal.mess_id == mess_id, Meal.date >= start, Meal.date <= end,
                           Meal.taken.is_(True))
        .all()
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
            "daily_bazar": round(daily_bazar, 2),
            "cumulative_bazar": round(cum_bazar, 2),
            "daily_meals": daily_meals,
            "cumulative_meals": cum_meals,
            "running_rate": round(rate, 2),
        })
    return history


def get_month_totals(mess_id, year, month):
    start, end = month_date_range(year, month)
    total_bazar = (
        db.session.query(db.func.coalesce(db.func.sum(Bazar.amount), 0.0))
        .filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
        .scalar()
    )
    total_meals = (
        Meal.query.filter(Meal.mess_id == mess_id, Meal.date >= start, Meal.date <= end,
                           Meal.taken.is_(True))
        .count()
    )
    total_deposits = (
        db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0.0))
        .filter(Deposit.mess_id == mess_id, Deposit.date >= start, Deposit.date <= end)
        .scalar()
    )
    final_rate = safe_div(total_bazar, total_meals)
    return {
        "total_bazar": round(total_bazar, 2),
        "total_meals": total_meals,
        "total_deposits": round(total_deposits, 2),
        "final_rate": round(final_rate, 2),
    }


def get_member_settlement(mess_id, year, month):
    """Return per-member settlement list for the given month."""
    start, end = month_date_range(year, month)
    totals = get_month_totals(mess_id, year, month)
    final_rate = totals["final_rate"]

    members = Member.query.filter_by(mess_id=mess_id).order_by(Member.name.asc()).all()
    results = []
    for mem in members:
        b_count = Meal.query.filter_by(mess_id=mess_id, member_id=mem.id, meal_type="breakfast",
                                        taken=True).filter(Meal.date >= start, Meal.date <= end).count()
        l_count = Meal.query.filter_by(mess_id=mess_id, member_id=mem.id, meal_type="lunch",
                                        taken=True).filter(Meal.date >= start, Meal.date <= end).count()
        d_count = Meal.query.filter_by(mess_id=mess_id, member_id=mem.id, meal_type="dinner",
                                        taken=True).filter(Meal.date >= start, Meal.date <= end).count()
        total_meals = b_count + l_count + d_count
        meal_cost = round(total_meals * final_rate, 2)

        total_deposit = (
            db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0.0))
            .filter(Deposit.mess_id == mess_id, Deposit.member_id == mem.id,
                    Deposit.date >= start, Deposit.date <= end)
            .scalar()
        )
        total_deposit = round(total_deposit, 2)
        balance = round(total_deposit - meal_cost, 2)

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
