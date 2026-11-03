import csv
import io
from models.member import Member
from models.bazar import Bazar
from models.deposit import Deposit
from services.settlement_service import SettlementService
from utils.dates import month_date_range, get_month_name


class ReportService:
    @staticmethod
    def get_monthly_report(mess_id, year, month):
        totals = SettlementService.get_month_totals(mess_id, year, month)
        settlement = SettlementService.get_member_settlement(mess_id, year, month)
        total_members = Member.query.filter_by(mess_id=mess_id).count()
        return {
            "year": year,
            "month": month,
            "month_name": get_month_name(month),
            "totals": totals,
            "settlement": settlement,
            "total_members": total_members,
        }

    @staticmethod
    def get_yearly_report(mess_id, year):
        yearly_rows = []
        for m in range(1, 13):
            t = SettlementService.get_month_totals(mess_id, year, m)
            if t["total_meals"] == 0 and t["total_bazar"] == 0 and t["total_deposits"] == 0:
                continue
            yearly_rows.append({
                "month": m,
                "month_name": get_month_name(m),
                **t
            })
        return yearly_rows

    @staticmethod
    def export_settlement_csv(mess_id, year, month):
        settlement = SettlementService.get_member_settlement(mess_id, year, month)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Member", "Breakfast", "Lunch", "Dinner", "Total Meals",
            "Meal Cost", "Total Deposit", "Balance", "Status"
        ])
        for row in settlement:
            writer.writerow([
                row["member"].name, row["breakfast"], row["lunch"], row["dinner"],
                row["total_meals"], row["meal_cost"], row["total_deposit"],
                row["balance"], row["status"]
            ])
        return output.getvalue()

    @staticmethod
    def export_members_csv(mess_id):
        members = Member.query.filter_by(mess_id=mess_id).order_by(Member.name.asc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Member ID", "Name", "Phone", "Joining Date", "Status"])
        for m in members:
            writer.writerow([m.id, m.name, m.phone or "", m.joining_date, m.status])
        return output.getvalue()

    @staticmethod
    def export_bazar_csv(mess_id, year, month):
        start, end = month_date_range(year, month)
        entries = (
            Bazar.query.filter_by(mess_id=mess_id)
            .filter(Bazar.date >= start, Bazar.date <= end)
            .order_by(Bazar.date.asc())
            .all()
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Member", "Category", "Amount", "Items"])
        for e in entries:
            writer.writerow([
                e.date,
                e.member.name if e.member else "",
                getattr(e, "category", "Groceries") or "Groceries",
                e.amount,
                e.items_description or ""
            ])
        return output.getvalue()

    @staticmethod
    def export_deposits_csv(mess_id, year, month):
        start, end = month_date_range(year, month)
        entries = (
            Deposit.query.filter_by(mess_id=mess_id)
            .filter(Deposit.date >= start, Deposit.date <= end)
            .order_by(Deposit.date.asc())
            .all()
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Member", "Payment Method", "Amount", "Note"])
        for e in entries:
            writer.writerow([
                e.date,
                e.member.name if e.member else "",
                getattr(e, "payment_method", "Cash") or "Cash",
                e.amount,
                e.note or ""
            ])
        return output.getvalue()
