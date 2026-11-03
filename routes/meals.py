from datetime import date
from flask import Blueprint, render_template, request, jsonify

from models.member import Member
from services.meal_service import MealService, MEAL_TYPES
from utils.dates import days_in_month
from utils.security import login_required, current_mess

bp = Blueprint("meals", __name__)


@bp.route("/meals")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    members = (
        Member.query.filter_by(mess_id=mess.id, status="Active")
        .order_by(Member.name.asc())
        .all()
    )
    day_count = days_in_month(year, month)
    days = list(range(1, day_count + 1))

    meal_map = MealService.get_month_meal_matrix(mess.id, year, month)

    return render_template(
        "meals.html",
        members=members,
        days=days,
        year=year,
        month=month,
        today_day=today.day if today.year == year and today.month == month else None,
        meal_map=meal_map,
        meal_types=MEAL_TYPES,
    )


@bp.route("/meals/toggle", methods=["POST"])
@login_required
def toggle():
    mess = current_mess()
    data = request.get_json(silent=True) or request.form

    try:
        member_id = int(data.get("member_id"))
        year = int(data.get("year"))
        month = int(data.get("month"))
        day = int(data.get("day"))
        meal_type = str(data.get("meal_type", "")).strip().lower()
        taken = str(data.get("taken")).lower() in ("true", "1", "yes")
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid request parameters."}), 400

    if meal_type not in MEAL_TYPES:
        return jsonify({"ok": False, "error": "Invalid meal type."}), 400

    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first()
    if not member:
        return jsonify({"ok": False, "error": "Member not found."}), 404

    try:
        new_taken = MealService.toggle_meal(
            mess_id=mess.id,
            member_id=member_id,
            year=year,
            month=month,
            day=day,
            meal_type=meal_type,
            taken=taken
        )
        return jsonify({"ok": True, "taken": new_taken})
    except ValueError as val_err:
        return jsonify({"ok": False, "error": str(val_err)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "Save failed. Please try again."}), 500
