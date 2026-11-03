from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from models.member import Member
from services.bazar_service import BazarService
from utils.security import login_required, current_mess

bp = Blueprint("bazar", __name__)


@bp.route("/bazar")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    entries = BazarService.get_entries(mess.id, year, month)
    members = (
        Member.query.filter_by(mess_id=mess.id, status="Active")
        .order_by(Member.name.asc())
        .all()
    )

    daily_totals = BazarService.get_daily_totals(entries)
    month_total = BazarService.get_month_total(mess.id, year, month)
    categories = BazarService.get_category_breakdown(mess.id, year, month)

    return render_template(
        "bazar.html",
        entries=entries,
        members=members,
        year=year,
        month=month,
        daily_totals=daily_totals,
        month_total=month_total,
        categories=categories,
    )


@bp.route("/bazar/add", methods=["POST"])
@login_required
def add():
    mess = current_mess()
    year = request.form.get("year", type=int)
    month = request.form.get("month", type=int)
    member_id = request.form.get("member_id", type=int)
    entry_date = request.form.get("date")
    amount = request.form.get("amount")
    items = request.form.get("items_description")
    category = request.form.get("category", "Groceries")

    try:
        entry = BazarService.add_entry(
            mess_id=mess.id,
            member_id=member_id,
            entry_date=entry_date,
            amount=amount,
            items_description=items,
            category=category,
        )
        flash("Bazar entry added successfully.", "success")
        return redirect(url_for("bazar.index", year=entry.date.year, month=entry.date.month))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("bazar.index", year=year, month=month))


@bp.route("/bazar/<int:entry_id>/edit", methods=["POST"])
@login_required
def edit(entry_id):
    mess = current_mess()
    entry = BazarService.get_entry(mess.id, entry_id)
    if not entry:
        abort(404)

    member_id = request.form.get("member_id", type=int)
    entry_date = request.form.get("date")
    amount = request.form.get("amount")
    items = request.form.get("items_description")
    category = request.form.get("category", "Groceries")

    try:
        updated = BazarService.update_entry(
            mess_id=mess.id,
            entry_id=entry_id,
            member_id=member_id,
            entry_date=entry_date,
            amount=amount,
            items_description=items,
            category=category,
        )
        flash("Bazar entry updated. Meal rate recalculated.", "success")
        return redirect(url_for("bazar.index", year=updated.date.year, month=updated.date.month))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("bazar.index", year=entry.date.year, month=entry.date.month))


@bp.route("/bazar/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    mess = current_mess()
    result = BazarService.delete_entry(mess.id, entry_id)
    if not result:
        abort(404)

    year, month = result
    flash("Bazar entry deleted. Meal rate recalculated.", "info")
    return redirect(url_for("bazar.index", year=year, month=month))
