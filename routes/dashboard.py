from datetime import date
from flask import Blueprint, render_template, request

from models.member import Member
from services.settlement_service import SettlementService
from services.bazar_service import BazarService
from utils.security import login_required, current_mess
from utils.currency import round_currency

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

    history = SettlementService.get_daily_history(mess.id, year, month)
    totals = SettlementService.get_month_totals(mess.id, year, month)
    settlement = SettlementService.get_member_settlement(mess.id, year, month)

    total_members = Member.query.filter_by(mess_id=mess.id).count()
    active_members = Member.query.filter_by(mess_id=mess.id, status="Active").count()

    current_running_rate = history[-1]["running_rate"] if history else 0.0

    total_due = sum(-s["balance"] for s in settlement if s["status"] == "due")
    total_refund = sum(s["balance"] for s in settlement if s["status"] == "refund")

    # Target rate comparison & alert
    warning = None
    target = mess.target_meal_rate
    if target is not None and current_running_rate > target:
        warning = round_currency(current_running_rate - target)

    # Category breakdown for charts
    categories = BazarService.get_category_breakdown(mess.id, year, month)

    return render_template(
        "dashboard.html",
        mess=mess,
        year=year,
        month=month,
        history=history,
        totals=totals,
        settlement=settlement,
        total_members=total_members,
        active_members=active_members,
        current_running_rate=current_running_rate,
        total_due=round_currency(total_due),
        total_refund=round_currency(total_refund),
        target=target,
        warning=warning,
        categories=categories,
    )
