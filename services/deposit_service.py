from datetime import date
from models import db
from models.deposit import Deposit
from models.member import Member
from utils.dates import parse_date, month_date_range
from utils.currency import round_currency


class DepositService:
    @staticmethod
    def get_entries(mess_id, year, month):
        start, end = month_date_range(year, month)
        return (
            Deposit.query.filter_by(mess_id=mess_id)
            .filter(Deposit.date >= start, Deposit.date <= end)
            .order_by(Deposit.date.desc(), Deposit.id.desc())
            .all()
        )

    @staticmethod
    def get_entry(mess_id, entry_id):
        return Deposit.query.filter_by(id=entry_id, mess_id=mess_id).first()

    @staticmethod
    def add_entry(mess_id, member_id, entry_date, amount, payment_method="Cash", note=None):
        try:
            amt = float(amount)
            if amt < 0:
                raise ValueError("Amount cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Please provide a valid, non-negative deposit amount.")

        member = Member.query.filter_by(id=member_id, mess_id=mess_id).first()
        if not member:
            raise ValueError("Please select a valid member.")

        d = parse_date(entry_date, default=date.today())
        clean_note = (note or "").strip() or None
        method = (payment_method or "Cash").strip()

        entry = Deposit(
            mess_id=mess_id,
            member_id=member.id,
            date=d,
            amount=round_currency(amt),
            payment_method=method,
            note=clean_note,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def update_entry(mess_id, entry_id, member_id, entry_date, amount, payment_method="Cash", note=None):
        entry = DepositService.get_entry(mess_id, entry_id)
        if not entry:
            return None

        try:
            amt = float(amount)
            if amt < 0:
                raise ValueError("Amount cannot be negative.")
        except (TypeError, ValueError):
            raise ValueError("Please provide a valid, non-negative deposit amount.")

        member = Member.query.filter_by(id=member_id, mess_id=mess_id).first()
        if not member:
            raise ValueError("Please select a valid member.")

        d = parse_date(entry_date, default=entry.date)
        clean_note = (note or "").strip() or None
        method = (payment_method or "Cash").strip()

        entry.member_id = member.id
        entry.date = d
        entry.amount = round_currency(amt)
        entry.payment_method = method
        entry.note = clean_note

        db.session.commit()
        return entry

    @staticmethod
    def delete_entry(mess_id, entry_id):
        entry = DepositService.get_entry(mess_id, entry_id)
        if not entry:
            return None
        year, month = entry.date.year, entry.date.month
        db.session.delete(entry)
        db.session.commit()
        return (year, month)

    @staticmethod
    def get_month_total(mess_id, year, month):
        start, end = month_date_range(year, month)
        total = (
            db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0.0))
            .filter(Deposit.mess_id == mess_id, Deposit.date >= start, Deposit.date <= end)
            .scalar()
        )
        return round_currency(total)
