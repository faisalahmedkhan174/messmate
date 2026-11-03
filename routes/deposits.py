from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from models.member import Member
from services.deposit_service import DepositService
from utils.security import login_required, current_mess

bp = Blueprint("deposits", __name__)


@bp.route("/deposits")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    entries = DepositService.get_entries(mess.id, year, month)
    members = (
        Member.query.filter_by(mess_id=mess.id, status="Active")
        .order_by(Member.name.asc())
        .all()
    )
    month_total = DepositService.get_month_total(mess.id, year, month)

    return render_template(
        "deposits.html",
        entries=entries,
        members=members,
        year=year,
        month=month,
        month_total=month_total,
    )


@bp.route("/deposits/add", methods=["POST"])
@login_required
def add():
    mess = current_mess()
    year = request.form.get("year", type=int)
    month = request.form.get("month", type=int)
    member_id = request.form.get("member_id", type=int)
    entry_date = request.form.get("date")
    amount = request.form.get("amount")
    payment_method = request.form.get("payment_method", "Cash")
    note = request.form.get("note")

    try:
        entry = DepositService.add_entry(
            mess_id=mess.id,
            member_id=member_id,
            entry_date=entry_date,
            amount=amount,
            payment_method=payment_method,
            note=note,
        )
        flash("Deposit recorded successfully.", "success")
        return redirect(url_for("deposits.index", year=entry.date.year, month=entry.date.month))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("deposits.index", year=year, month=month))


@bp.route("/deposits/<int:entry_id>/edit", methods=["POST"])
@login_required
def edit(entry_id):
    mess = current_mess()
    entry = DepositService.get_entry(mess.id, entry_id)
    if not entry:
        abort(404)

    member_id = request.form.get("member_id", type=int)
    entry_date = request.form.get("date")
    amount = request.form.get("amount")
    payment_method = request.form.get("payment_method", "Cash")
    note = request.form.get("note")

    try:
        updated = DepositService.update_entry(
            mess_id=mess.id,
            entry_id=entry_id,
            member_id=member_id,
            entry_date=entry_date,
            amount=amount,
            payment_method=payment_method,
            note=note,
        )
        flash("Deposit updated. Settlement recalculated.", "success")
        return redirect(url_for("deposits.index", year=updated.date.year, month=updated.date.month))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("deposits.index", year=entry.date.year, month=entry.date.month))


@bp.route("/deposits/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    mess = current_mess()
    result = DepositService.delete_entry(mess.id, entry_id)
    if not result:
        abort(404)

    year, month = result
    flash("Deposit deleted. Settlement recalculated.", "info")
    return redirect(url_for("deposits.index", year=year, month=month))
