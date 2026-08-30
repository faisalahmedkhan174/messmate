from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from models import db
from models.member import Member
from .helpers import login_required, current_mess

bp = Blueprint("members", __name__)


def _parse_date(value, default=None):
    if not value:
        return default or date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default or date.today()


@bp.route("/members")
@login_required
def index():
    mess = current_mess()
    q = (request.args.get("q") or "").strip()
    status_filter = request.args.get("status", "all")

    query = Member.query.filter_by(mess_id=mess.id)
    if q:
        query = query.filter(Member.name.ilike(f"%{q}%"))
    if status_filter in ("Active", "Inactive"):
        query = query.filter_by(status=status_filter)

    members = query.order_by(Member.name.asc()).all()
    return render_template("members.html", members=members, q=q, status_filter=status_filter)


@bp.route("/members/add", methods=["POST"])
@login_required
def add():
    mess = current_mess()
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip() or None
    joining_date = _parse_date(request.form.get("joining_date"))

    if not name:
        flash("Member name is required.", "danger")
        return redirect(url_for("members.index"))

    member = Member(mess_id=mess.id, name=name, phone=phone, joining_date=joining_date,
                     status="Active")
    db.session.add(member)
    db.session.commit()
    flash(f"Member '{name}' added.", "success")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/edit", methods=["POST"])
@login_required
def edit(member_id):
    mess = current_mess()
    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first_or_404()

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Member name is required.", "danger")
        return redirect(url_for("members.index"))

    member.name = name
    member.phone = (request.form.get("phone") or "").strip() or None
    member.joining_date = _parse_date(request.form.get("joining_date"), member.joining_date)
    db.session.commit()
    flash("Member updated.", "success")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/toggle_status", methods=["POST"])
@login_required
def toggle_status(member_id):
    mess = current_mess()
    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first_or_404()
    member.status = "Inactive" if member.status == "Active" else "Active"
    db.session.commit()
    flash(f"{member.name} marked {member.status}.", "info")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete(member_id):
    mess = current_mess()
    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first_or_404()
    db.session.delete(member)
    db.session.commit()
    flash("Member deleted.", "info")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/details")
@login_required
def details(member_id):
    from datetime import date as _date
    from .helpers import month_date_range
    from models.meal import Meal
    from models.bazar import Bazar
    from models.deposit import Deposit

    mess = current_mess()
    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first_or_404()

    today = _date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    start, end = month_date_range(year, month)

    meals = (Meal.query.filter_by(mess_id=mess.id, member_id=member.id)
             .filter(Meal.date >= start, Meal.date <= end)
             .order_by(Meal.date.asc()).all())

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

    total_breakfast = sum(1 for m in meals if m.meal_type == "breakfast" and m.taken)
    total_lunch = sum(1 for m in meals if m.meal_type == "lunch" and m.taken)
    total_dinner = sum(1 for m in meals if m.meal_type == "dinner" and m.taken)
    total_meals = total_breakfast + total_lunch + total_dinner

    deposits = (Deposit.query.filter_by(mess_id=mess.id, member_id=member.id)
                .filter(Deposit.date >= start, Deposit.date <= end)
                .order_by(Deposit.date.asc()).all())
    total_deposits = round(sum(d.amount for d in deposits), 2)

    bazars = (Bazar.query.filter_by(mess_id=mess.id, member_id=member.id)
              .filter(Bazar.date >= start, Bazar.date <= end)
              .order_by(Bazar.date.asc()).all())

    from .helpers import get_month_totals
    totals = get_month_totals(mess.id, year, month)
    final_rate = totals["final_rate"]
    meal_cost = round(total_meals * final_rate, 2)
    balance = round(total_deposits - meal_cost, 2)

    return render_template(
        "member_details.html",
        member=member, year=year, month=month,
        total_breakfast=total_breakfast, total_lunch=total_lunch,
        total_dinner=total_dinner, total_meals=total_meals,
        total_deposits=total_deposits, meal_cost=meal_cost, balance=balance,
        daily_meal_history=daily_meal_history,
        deposits=deposits, bazars=bazars,
    )
