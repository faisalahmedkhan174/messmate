"""
Backward-compatibility facade for route helpers.
Delegates calculations and operations to the clean service and utils layers.
"""
from utils.dates import days_in_month, month_date_range
from utils.currency import safe_div
from utils.security import login_required, creator_required, current_mess, current_user
from services.meal_service import MEAL_TYPES
from services.settlement_service import SettlementService


def get_daily_history(mess_id, year, month):
    return SettlementService.get_daily_history(mess_id, year, month)


def get_month_totals(mess_id, year, month):
    return SettlementService.get_month_totals(mess_id, year, month)


def get_member_settlement(mess_id, year, month):
    return SettlementService.get_member_settlement(mess_id, year, month)
