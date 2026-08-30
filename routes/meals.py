from datetime import date

from flask import Blueprint, render_template, request, jsonify

from models import db
from models.member import Member
from models.meal import Meal
from .helpers import login_required, current_mess, days_in_month, MEAL_TYPES

bp = Blueprint("meals", __name__)


@bp.route("/meals")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    members = Member.query.filter_by(mess_id=mess.id, status="Active").order_by(Member.name.asc()).all()
    day_count = days_in_month(year, month)
    days = list(range(1, day_count + 1))

    meal_rows = Meal.query.filter(
        Meal.mess_id == mess.id,
        db.extract("year", Meal.date) == year,
        db.extract("month", Meal.date) == month,
    ).all()

    # meal_map[member_id][day][meal_type] = taken (bool)
    meal_map = {}
    for m in meal_rows:
        meal_map.setdefault(m.member_id, {}).setdefault(m.date.day, {})[m.meal_type] = m.taken

    return render_template(
        "meals.html",
        members=members, days=days, year=year, month=month,
        meal_map=meal_map, meal_types=MEAL_TYPES,
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
        meal_type = data.get("meal_type")
        taken = str(data.get("taken")).lower() in ("true", "1", "yes")
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid request data."}), 400

    if meal_type not in MEAL_TYPES:
        return jsonify({"ok": False, "error": "Invalid meal type."}), 400

    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first()
    if not member:
        return jsonify({"ok": False, "error": "Member not found."}), 404

    try:
        meal_date = date(year, month, day)
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid date."}), 400

    try:
        record = Meal.query.filter_by(
            mess_id=mess.id, member_id=member_id, date=meal_date, meal_type=meal_type
        ).first()
        if record:
            record.taken = taken
        else:
            record = Meal(mess_id=mess.id, member_id=member_id, date=meal_date,
                           meal_type=meal_type, taken=taken)
            db.session.add(record)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"ok": False, "error": "Save failed. Please try again."}), 500

    return jsonify({"ok": True, "taken": taken})
