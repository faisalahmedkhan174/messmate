from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from services.member_service import MemberService
from utils.security import login_required, current_mess

bp = Blueprint("members", __name__)


@bp.route("/members")
@login_required
def index():
    mess = current_mess()
    q = (request.args.get("q") or "").strip()
    status_filter = request.args.get("status", "all")

    members = MemberService.get_members(mess.id, search_query=q, status_filter=status_filter)
    return render_template("members.html", members=members, q=q, status_filter=status_filter)


@bp.route("/members/add", methods=["POST"])
@login_required
def add():
    mess = current_mess()
    name = request.form.get("name")
    phone = request.form.get("phone")
    joining_date = request.form.get("joining_date")

    try:
        member = MemberService.add_member(
            mess_id=mess.id,
            name=name,
            phone=phone,
            joining_date=joining_date
        )
        flash(f"Member '{member.name}' added successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/edit", methods=["POST"])
@login_required
def edit(member_id):
    mess = current_mess()
    name = request.form.get("name")
    phone = request.form.get("phone")
    joining_date = request.form.get("joining_date")

    member = MemberService.get_member(mess.id, member_id)
    if not member:
        abort(404)

    try:
        MemberService.update_member(
            mess_id=mess.id,
            member_id=member_id,
            name=name,
            phone=phone,
            joining_date=joining_date
        )
        flash("Member details updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/toggle_status", methods=["POST"])
@login_required
def toggle_status(member_id):
    mess = current_mess()
    member = MemberService.get_member(mess.id, member_id)
    if not member:
        abort(404)

    MemberService.toggle_status(mess.id, member_id)
    flash(f"Member '{member.name}' marked {member.status}.", "info")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete(member_id):
    mess = current_mess()
    member = MemberService.get_member(mess.id, member_id)
    if not member:
        abort(404)

    MemberService.delete_member(mess.id, member_id)
    flash("Member deleted successfully.", "info")
    return redirect(url_for("members.index"))


@bp.route("/members/<int:member_id>/details")
@login_required
def details(member_id):
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    details_data = MemberService.get_member_details(mess.id, member_id, year, month)
    if not details_data:
        abort(404)

    return render_template("member_details.html", **details_data)
