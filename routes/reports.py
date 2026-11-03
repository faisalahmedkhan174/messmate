from datetime import date
from flask import Blueprint, render_template, request, Response

from services.report_service import ReportService
from utils.security import login_required, current_mess

bp = Blueprint("reports", __name__)


@bp.route("/reports")
@login_required
def index():
    mess = current_mess()
    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month

    monthly_data = ReportService.get_monthly_report(mess.id, year, month)
    yearly_rows = ReportService.get_yearly_report(mess.id, year)

    return render_template(
        "reports.html",
        mess=mess,
        year=year,
        month=month,
        totals=monthly_data["totals"],
        settlement=monthly_data["settlement"],
        total_members=monthly_data["total_members"],
        yearly_rows=yearly_rows,
    )


@bp.route("/reports/export/settlement.csv")
@login_required
def export_settlement_csv():
    mess = current_mess()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    csv_data = ReportService.export_settlement_csv(mess.id, year, month)
    filename = f"settlement_{mess.id}_{year}_{month:02d}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@bp.route("/reports/export/members.csv")
@login_required
def export_members_csv():
    mess = current_mess()
    csv_data = ReportService.export_members_csv(mess.id)
    filename = f"members_{mess.id}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@bp.route("/reports/export/bazar.csv")
@login_required
def export_bazar_csv():
    mess = current_mess()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    csv_data = ReportService.export_bazar_csv(mess.id, year, month)
    filename = f"bazar_{mess.id}_{year}_{month:02d}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@bp.route("/reports/export/deposits.csv")
@login_required
def export_deposits_csv():
    mess = current_mess()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    csv_data = ReportService.export_deposits_csv(mess.id, year, month)
    filename = f"deposits_{mess.id}_{year}_{month:02d}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
