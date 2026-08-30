from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import db
from models.member import Member
from models.deposit import Deposit
from .helpers import login_required, current_mess, month_date_range

bp = Blueprint("deposits", __name__)


def _parse_date(value, default=None):
    if not value:
        return default or date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default or date.today()


@bp.route("/deposits")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    start, end = month_date_range(year, month)

    entries = (Deposit.query.filter_by(mess_id=mess.id)
               .filter(Deposit.date >= start, Deposit.date <= end)
               .order_by(Deposit.date.desc(), Deposit.id.desc()).all())

    members = Member.query.filter_by(mess_id=mess.id, status="Active").order_by(Member.name.asc()).all()
    month_total = round(sum(e.amount for e in entries), 2)

    return render_template("deposits.html", entries=entries, members=members, year=year, month=month,
                            month_total=month_total)


@bp.route("/deposits/add", methods=["POST"])
@login_required
def add():
    mess = current_mess()
    year = request.form.get("year", type=int)
    month = request.form.get("month", type=int)
    member_id = request.form.get("member_id", type=int)
    entry_date = _parse_date(request.form.get("date"))
    amount_raw = request.form.get("amount")
    note = (request.form.get("note") or "").strip() or None

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        flash("Please enter a valid deposit amount.", "danger")
        return redirect(url_for("deposits.index", year=year, month=month))

    if amount < 0:
        flash("Deposit amount cannot be negative.", "danger")
        return redirect(url_for("deposits.index", year=year, month=month))

    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first()
    if not member:
        flash("Please select a valid member for this deposit.", "danger")
        return redirect(url_for("deposits.index", year=year, month=month))

    entry = Deposit(mess_id=mess.id, member_id=member.id, date=entry_date, amount=amount, note=note)
    db.session.add(entry)
    db.session.commit()
    flash("Deposit recorded.", "success")
    return redirect(url_for("deposits.index", year=entry_date.year, month=entry_date.month))


@bp.route("/deposits/<int:entry_id>/edit", methods=["POST"])
@login_required
def edit(entry_id):
    mess = current_mess()
    entry = Deposit.query.filter_by(id=entry_id, mess_id=mess.id).first_or_404()

    member_id = request.form.get("member_id", type=int)
    entry_date = _parse_date(request.form.get("date"), entry.date)
    amount_raw = request.form.get("amount")
    note = (request.form.get("note") or "").strip() or None

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        flash("Please enter a valid deposit amount.", "danger")
        return redirect(url_for("deposits.index", year=entry.date.year, month=entry.date.month))

    if amount < 0:
        flash("Deposit amount cannot be negative.", "danger")
        return redirect(url_for("deposits.index", year=entry.date.year, month=entry.date.month))

    member = Member.query.filter_by(id=member_id, mess_id=mess.id).first()
    if member:
        entry.member_id = member.id
    entry.date = entry_date
    entry.amount = amount
    entry.note = note
    db.session.commit()
    flash("Deposit updated. Settlement recalculated.", "success")
    return redirect(url_for("deposits.index", year=entry_date.year, month=entry_date.month))


@bp.route("/deposits/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    mess = current_mess()
    entry = Deposit.query.filter_by(id=entry_id, mess_id=mess.id).first_or_404()
    y, m = entry.date.year, entry.date.month
    db.session.delete(entry)
    db.session.commit()
    flash("Deposit deleted. Settlement recalculated.", "info")
    return redirect(url_for("deposits.index", year=y, month=m))
