from datetime import date

from flask import Blueprint, render_template, request

from models.member import Member
from .helpers import (login_required, current_mess, get_daily_history,
                       get_month_totals, get_member_settlement)

bp = Blueprint("dashboard", __name__)


def _selected_year_month():
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    return year, month


@bp.route("/")
@bp.route("/dashboard")
@login_required
def index():
    mess = current_mess()
    year, month = _selected_year_month()

    history = get_daily_history(mess.id, year, month)
    totals = get_month_totals(mess.id, year, month)
    settlement = get_member_settlement(mess.id, year, month)

    total_members = Member.query.filter_by(mess_id=mess.id).count()
    active_members = Member.query.filter_by(mess_id=mess.id, status="Active").count()

    current_running_rate = history[-1]["running_rate"] if history else 0.0

    total_due = sum(-s["balance"] for s in settlement if s["status"] == "due")
    total_refund = sum(s["balance"] for s in settlement if s["status"] == "refund")

    warning = None
    target = mess.target_meal_rate
    if target is not None and current_running_rate > target:
        warning = round(current_running_rate - target, 2)

    return render_template(
        "dashboard.html",
        mess=mess,
        year=year, month=month,
        history=history,
        totals=totals,
        settlement=settlement,
        total_members=total_members,
        active_members=active_members,
        current_running_rate=current_running_rate,
        total_due=round(total_due, 2),
        total_refund=round(total_refund, 2),
        target=target,
        warning=warning,
    )
