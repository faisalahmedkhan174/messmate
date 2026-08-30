import csv
import io
from datetime import date

from flask import Blueprint, render_template, request, Response

from models.member import Member
from .helpers import (login_required, current_mess, get_month_totals,
                       get_member_settlement, days_in_month)

bp = Blueprint("reports", __name__)


@bp.route("/reports")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    totals = get_month_totals(mess.id, year, month)
    settlement = get_member_settlement(mess.id, year, month)
    total_members = Member.query.filter_by(mess_id=mess.id).count()

    yearly_rows = []
    for m in range(1, 13):
        # Skip future months of the current year beyond today, still show for clarity if data exists
        t = get_month_totals(mess.id, year, m)
        if t["total_meals"] == 0 and t["total_bazar"] == 0:
            continue
        yearly_rows.append({"month": m, **t})

    return render_template("reports.html", mess=mess, year=year, month=month,
                            totals=totals, settlement=settlement,
                            total_members=total_members, yearly_rows=yearly_rows)


@bp.route("/reports/export/settlement.csv")
@login_required
def export_settlement_csv():
    mess = current_mess()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    settlement = get_member_settlement(mess.id, year, month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Member", "Breakfast", "Lunch", "Dinner", "Total Meals",
                      "Meal Cost", "Total Deposit", "Balance", "Status"])
    for row in settlement:
        writer.writerow([row["member"].name, row["breakfast"], row["lunch"], row["dinner"],
                          row["total_meals"], row["meal_cost"], row["total_deposit"],
                          row["balance"], row["status"]])

    filename = f"settlement_{mess.id}_{year}_{month:02d}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename={filename}"})


@bp.route("/reports/export/members.csv")
@login_required
def export_members_csv():
    mess = current_mess()
    members = Member.query.filter_by(mess_id=mess.id).order_by(Member.name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Member ID", "Name", "Phone", "Joining Date", "Status"])
    for m in members:
        writer.writerow([m.id, m.name, m.phone or "", m.joining_date, m.status])

    filename = f"members_{mess.id}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename={filename}"})


@bp.route("/reports/export/bazar.csv")
@login_required
def export_bazar_csv():
    from models.bazar import Bazar
    from .helpers import month_date_range

    mess = current_mess()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month
    start, end = month_date_range(year, month)

    entries = (Bazar.query.filter_by(mess_id=mess.id)
               .filter(Bazar.date >= start, Bazar.date <= end)
               .order_by(Bazar.date.asc()).all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Member", "Amount", "Items"])
    for e in entries:
        writer.writerow([e.date, e.member.name, e.amount, e.items_description or ""])

    filename = f"bazar_{mess.id}_{year}_{month:02d}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename={filename}"})
