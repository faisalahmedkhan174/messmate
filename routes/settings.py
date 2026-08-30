import json
import random
from datetime import date, timedelta

from flask import (Blueprint, render_template, request, redirect, url_for,
                    flash, session, jsonify)

from models import db
from models.user import User
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit
from .helpers import login_required, current_mess

bp = Blueprint("settings", __name__)


@bp.route("/settings")
@login_required
def index():
    mess = current_mess()
    user = User.query.filter_by(id=session.get("user_id"), mess_id=mess.id).first()
    return render_template("settings.html", mess=mess, user=user)


@bp.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    mess = current_mess()
    user = User.query.filter_by(id=session.get("user_id"), mess_id=mess.id).first_or_404()

    mess_name = (request.form.get("mess_name") or "").strip()
    manager_name = (request.form.get("manager_name") or "").strip()
    username = (request.form.get("username") or "").strip()

    if not mess_name or not manager_name or not username:
        flash("Mess name, manager name, and username cannot be empty.", "danger")
        return redirect(url_for("settings.index"))

    existing = User.query.filter(User.mess_id == mess.id, User.username == username,
                                  User.id != user.id).first()
    if existing:
        flash("That username is already in use for this mess.", "danger")
        return redirect(url_for("settings.index"))

    mess.name = mess_name
    mess.manager_name = manager_name
    user.manager_name = manager_name
    user.username = username
    db.session.commit()

    session["manager_name"] = manager_name
    session["mess_name"] = mess_name

    flash("Profile settings updated.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/settings/password", methods=["POST"])
@login_required
def update_password():
    mess = current_mess()
    user = User.query.filter_by(id=session.get("user_id"), mess_id=mess.id).first_or_404()

    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("settings.index"))
    if len(new_password) < 4:
        flash("New password should be at least 4 characters.", "danger")
        return redirect(url_for("settings.index"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("settings.index"))

    user.set_password(new_password)
    db.session.commit()
    flash("Password updated successfully.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/settings/target", methods=["POST"])
@login_required
def update_target():
    mess = current_mess()
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
            return redirect(url_for("settings.index"))

    db.session.commit()
    flash("Target meal rate updated.", "success")
    return redirect(url_for("settings.index"))


@bp.route("/settings/demo_data", methods=["POST"])
@login_required
def load_demo_data():
    mess = current_mess()
    today = date.today()
    year, month = today.year, today.month

    demo_names = ["Rahim", "Karim", "Hasan", "Jamal", "Sabbir", "Nayeem"]
    members = []
    for i, name in enumerate(demo_names):
        existing = Member.query.filter_by(mess_id=mess.id, name=name).first()
        if existing:
            members.append(existing)
            continue
        m = Member(mess_id=mess.id, name=name, phone=None,
                   joining_date=date(year, month, 1), status="Active")
        db.session.add(m)
        members.append(m)
    db.session.flush()

    day_count = min(10, (today.day if today.month == month and today.year == year else 28))
    meal_types = ["breakfast", "lunch", "dinner"]

    for day_num in range(1, day_count + 1):
        d = date(year, month, day_num)
        for m in members:
            for mt in meal_types:
                if Meal.query.filter_by(mess_id=mess.id, member_id=m.id, date=d,
                                         meal_type=mt).first():
                    continue
                taken = random.random() > 0.15
                db.session.add(Meal(mess_id=mess.id, member_id=m.id, date=d,
                                     meal_type=mt, taken=taken))
        bazar_member = random.choice(members)
        db.session.add(Bazar(mess_id=mess.id, member_id=bazar_member.id, date=d,
                              amount=round(random.uniform(700, 2000), 2),
                              items_description="Demo groceries"))

    for m in members:
        db.session.add(Deposit(mess_id=mess.id, member_id=m.id,
                                date=date(year, month, 1), amount=3000, note="Demo deposit"))

    if mess.target_meal_rate is None:
        mess.target_meal_rate = 55.0

    db.session.commit()
    flash("Demo data loaded for the current month.", "success")
    return redirect(url_for("dashboard.index", year=year, month=month))


@bp.route("/settings/backup.json")
@login_required
def backup_json():
    mess = current_mess()
    members = Member.query.filter_by(mess_id=mess.id).all()
    meals = Meal.query.filter_by(mess_id=mess.id).all()
    bazars = Bazar.query.filter_by(mess_id=mess.id).all()
    deposits = Deposit.query.filter_by(mess_id=mess.id).all()

    data = {
        "mess": {"name": mess.name, "manager_name": mess.manager_name,
                 "target_meal_rate": mess.target_meal_rate},
        "members": [{"id": m.id, "name": m.name, "phone": m.phone,
                     "joining_date": m.joining_date.isoformat(), "status": m.status}
                    for m in members],
        "meals": [{"member_id": m.member_id, "date": m.date.isoformat(),
                   "meal_type": m.meal_type, "taken": m.taken} for m in meals],
        "bazar": [{"member_id": b.member_id, "date": b.date.isoformat(),
                   "amount": b.amount, "items_description": b.items_description}
                  for b in bazars],
        "deposits": [{"member_id": d.member_id, "date": d.date.isoformat(),
                      "amount": d.amount, "note": d.note} for d in deposits],
    }

    response = jsonify(data)
    response.headers["Content-Disposition"] = f"attachment; filename=messmate_backup_{mess.id}.json"
    return response
