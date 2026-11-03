import unittest
from datetime import date

from app import create_app
from models import db
from models.mess import Mess
from models.member import Member
from services.member_service import MemberService
from services.meal_service import MealService
from services.bazar_service import BazarService
from services.deposit_service import DepositService
from services.settlement_service import SettlementService
from services.report_service import ReportService


class ServicesTestCase(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-key"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test mess
        self.mess = Mess(name="Test Mess", manager_name="Manager John", target_meal_rate=50.0)
        db.session.add(self.mess)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_member_service_crud(self):
        # Add
        m = MemberService.add_member(self.mess.id, "Alice", "01700000000", "2026-08-01")
        self.assertIsNotNone(m.id)
        self.assertEqual(m.name, "Alice")
        self.assertEqual(m.status, "Active")

        # Update
        updated = MemberService.update_member(self.mess.id, m.id, "Alice Wonderland", "01800000000")
        self.assertEqual(updated.name, "Alice Wonderland")
        self.assertEqual(updated.phone, "01800000000")

        # Toggle status
        toggled = MemberService.toggle_status(self.mess.id, m.id)
        self.assertEqual(toggled.status, "Inactive")
        toggled_back = MemberService.toggle_status(self.mess.id, m.id)
        self.assertEqual(toggled_back.status, "Active")

        # Delete
        success = MemberService.delete_member(self.mess.id, m.id)
        self.assertTrue(success)
        self.assertIsNone(MemberService.get_member(self.mess.id, m.id))

    def test_meal_service_and_matrix(self):
        m = MemberService.add_member(self.mess.id, "Bob")
        # Toggle meal
        taken = MealService.toggle_meal(self.mess.id, m.id, 2026, 8, 1, "breakfast", True)
        self.assertTrue(taken)
        taken = MealService.toggle_meal(self.mess.id, m.id, 2026, 8, 1, "lunch", True)
        self.assertTrue(taken)

        # Toggle off
        taken_off = MealService.toggle_meal(self.mess.id, m.id, 2026, 8, 1, "breakfast", False)
        self.assertFalse(taken_off)

        # Check matrix
        matrix = MealService.get_month_meal_matrix(self.mess.id, 2026, 8)
        self.assertFalse(matrix[m.id][1]["breakfast"])
        self.assertTrue(matrix[m.id][1]["lunch"])

    def test_bazar_service_crud_and_categories(self):
        m = MemberService.add_member(self.mess.id, "Charlie")
        entry = BazarService.add_entry(
            self.mess.id, m.id, "2026-08-05", 1250.50,
            items_description="Fish and spices", category="Fish/Meat"
        )
        self.assertEqual(entry.amount, 1250.50)
        self.assertEqual(entry.category, "Fish/Meat")

        # Month total
        total = BazarService.get_month_total(self.mess.id, 2026, 8)
        self.assertEqual(total, 1250.50)

        # Category breakdown
        breakdown = BazarService.get_category_breakdown(self.mess.id, 2026, 8)
        self.assertIn("Fish/Meat", breakdown)
        self.assertEqual(breakdown["Fish/Meat"], 1250.50)

    def test_deposit_service_crud(self):
        m = MemberService.add_member(self.mess.id, "David")
        dep = DepositService.add_entry(
            self.mess.id, m.id, "2026-08-01", 3000.0,
            payment_method="bKash", note="August advance"
        )
        self.assertEqual(dep.amount, 3000.0)
        self.assertEqual(dep.payment_method, "bKash")

        total = DepositService.get_month_total(self.mess.id, 2026, 8)
        self.assertEqual(total, 3000.0)

    def test_settlement_batch_calculation(self):
        m1 = MemberService.add_member(self.mess.id, "User1")
        m2 = MemberService.add_member(self.mess.id, "User2")

        # Meals
        MealService.toggle_meal(self.mess.id, m1.id, 2026, 8, 1, "breakfast", True)
        MealService.toggle_meal(self.mess.id, m1.id, 2026, 8, 1, "lunch", True)
        MealService.toggle_meal(self.mess.id, m2.id, 2026, 8, 1, "lunch", True)

        # Bazar 300 -> 3 meals total -> rate 100
        BazarService.add_entry(self.mess.id, m1.id, "2026-08-01", 300.0, "Groceries")

        # Deposits
        DepositService.add_entry(self.mess.id, m1.id, "2026-08-01", 250.0)
        DepositService.add_entry(self.mess.id, m2.id, "2026-08-01", 50.0)

        settlement = SettlementService.get_member_settlement(self.mess.id, 2026, 8)
        settle_map = {s["member"].name: s for s in settlement}

        # User1: 2 meals * 100 = 200 meal cost. Deposit = 250. Balance = +50 -> refund
        self.assertEqual(settle_map["User1"]["total_meals"], 2)
        self.assertEqual(settle_map["User1"]["meal_cost"], 200.0)
        self.assertEqual(settle_map["User1"]["total_deposit"], 250.0)
        self.assertEqual(settle_map["User1"]["balance"], 50.0)
        self.assertEqual(settle_map["User1"]["status"], "refund")

        # User2: 1 meal * 100 = 100 meal cost. Deposit = 50. Balance = -50 -> due
        self.assertEqual(settle_map["User2"]["total_meals"], 1)
        self.assertEqual(settle_map["User2"]["meal_cost"], 100.0)
        self.assertEqual(settle_map["User2"]["total_deposit"], 50.0)
        self.assertEqual(settle_map["User2"]["balance"], -50.0)
        self.assertEqual(settle_map["User2"]["status"], "due")

    def test_report_service_csv_generation(self):
        m = MemberService.add_member(self.mess.id, "Exporter")
        DepositService.add_entry(self.mess.id, m.id, "2026-08-01", 1000.0)
        BazarService.add_entry(self.mess.id, m.id, "2026-08-01", 500.0, "Items", "Groceries")

        csv_settlement = ReportService.export_settlement_csv(self.mess.id, 2026, 8)
        self.assertIn("Exporter", csv_settlement)
        self.assertIn("Meal Cost", csv_settlement)

        csv_members = ReportService.export_members_csv(self.mess.id)
        self.assertIn("Exporter", csv_members)

        csv_bazar = ReportService.export_bazar_csv(self.mess.id, 2026, 8)
        self.assertIn("500", csv_bazar)

        csv_deposits = ReportService.export_deposits_csv(self.mess.id, 2026, 8)
        self.assertIn("1000", csv_deposits)


if __name__ == "__main__":
    unittest.main()
