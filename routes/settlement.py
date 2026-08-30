from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import db
from .helpers import login_required, current_mess, get_member_settlement, get_month_totals

bp = Blueprint("settlement", __name__)


@bp.route("/settlement")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    status_filter = request.args.get("status", "all")

    settlement = get_member_settlement(mess.id, year, month)
    if status_filter in ("due", "refund", "settled"):
        settlement = [s for s in settlement if s["status"] == status_filter]

    totals = get_month_totals(mess.id, year, month)

    return render_template("settlement.html", settlement=settlement, totals=totals,
                            year=year, month=month, status_filter=status_filter, mess=mess)


@bp.route("/settlement/target", methods=["POST"])
@login_required
def set_target():
    mess = current_mess()
    year = request.form.get("year", type=int)
    month = request.form.get("month", type=int)
    target_raw = (request.form.get("target_meal_rate") or "").strip()

    if target_raw == "":
        mess.target_meal_rate = None
    else:
        try:
            target = float(target_raw)
            if target < 0:
                raise ValueError
            mess.target_meal_rate = target
        except ValueError:
            flash("Please enter a valid, non-negative target meal rate.", "danger")
            return redirect(url_for("settlement.index", year=year, month=month))

    db.session.commit()
    flash("Target meal rate updated.", "success")
    return redirect(url_for("settlement.index", year=year, month=month))
