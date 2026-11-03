from datetime import date
from models import db
from models.bazar import Bazar
from models.member import Member
from utils.dates import parse_date, month_date_range
from utils.currency import round_currency


class BazarService:
    @staticmethod
    def get_entries(mess_id, year, month):
        start, end = month_date_range(year, month)
        return (
            Bazar.query.filter_by(mess_id=mess_id)
            .filter(Bazar.date >= start, Bazar.date <= end)
            .order_by(Bazar.date.desc(), Bazar.id.desc())
            .all()
        )

    @staticmethod
    def get_entry(mess_id, entry_id):
        return Bazar.query.filter_by(id=entry_id, mess_id=mess_id).first()

    @staticmethod
    def add_entry(mess_id, member_id, entry_date, amount, items_description=None, category="Groceries"):
        try:
            amt = float(amount)
            if amt < 0:
                raise ValueError("Amount cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Please provide a valid, non-negative bazar amount.")

        member = Member.query.filter_by(id=member_id, mess_id=mess_id).first()
        if not member:
            raise ValueError("Please select a valid member.")

        d = parse_date(entry_date, default=date.today())
        desc = (items_description or "").strip() or None
        cat = (category or "Groceries").strip()

        entry = Bazar(
            mess_id=mess_id,
            member_id=member.id,
            date=d,
            amount=round_currency(amt),
            items_description=desc,
            category=cat,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def update_entry(mess_id, entry_id, member_id, entry_date, amount, items_description=None, category="Groceries"):
        entry = BazarService.get_entry(mess_id, entry_id)
        if not entry:
            return None

        try:
            amt = float(amount)
            if amt < 0:
                raise ValueError("Amount cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Please provide a valid, non-negative bazar amount.")

        member = Member.query.filter_by(id=member_id, mess_id=mess_id).first()
        if not member:
            raise ValueError("Please select a valid member.")

        d = parse_date(entry_date, default=entry.date)
        desc = (items_description or "").strip() or None
        cat = (category or "Groceries").strip()

        entry.member_id = member.id
        entry.date = d
        entry.amount = round_currency(amt)
        entry.items_description = desc
        entry.category = cat

        db.session.commit()
        return entry

    @staticmethod
    def delete_entry(mess_id, entry_id):
        entry = BazarService.get_entry(mess_id, entry_id)
        if not entry:
            return None
        year, month = entry.date.year, entry.date.month
        db.session.delete(entry)
        db.session.commit()
        return (year, month)

    @staticmethod
    def get_daily_totals(entries):
        totals = {}
        for e in entries:
            totals[e.date] = round_currency(totals.get(e.date, 0.0) + e.amount)
        return totals

    @staticmethod
    def get_month_total(mess_id, year, month):
        start, end = month_date_range(year, month)
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Bazar.amount), 0.0))
            .filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
            .scalar()
        )
        return round_currency(total)

    @staticmethod
    def get_category_breakdown(mess_id, year, month):
        start, end = month_date_range(year, month)
        rows = (
            db.session.query(Bazar.category, db.func.sum(Bazar.amount))
            .filter(Bazar.mess_id == mess_id, Bazar.date >= start, Bazar.date <= end)
            .group_by(Bazar.category)
            .all()
        )
        return {r[0] or "Other": round_currency(r[1]) for r in rows}
