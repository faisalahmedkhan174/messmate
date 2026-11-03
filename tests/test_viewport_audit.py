import unittest
import re
import os
from app import create_app
from models import db
from models.mess import Mess
from models.user import User


class ViewportAndCSSAuditTestCase(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.mess = Mess(name="Viewport Mess", manager_name="Tester", target_meal_rate=50.0)
        db.session.add(self.mess)
        db.session.flush()
        self.user = User(mess_id=self.mess.id, username="tester", manager_name="Tester")
        self.user.set_password("pass123")
        db.session.add(self.user)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["mess_id"] = self.mess.id
            sess["user_id"] = self.user.id
            sess["mess_name"] = self.mess.name
            sess["manager_name"] = self.user.manager_name

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_css_rules_prevent_horizontal_overflow(self):
        css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # Check overflow-x hidden rule
        self.assertIn("overflow-x: hidden", css_content)
        # Check touch target size >= 40px
        self.assertIn("min-height: 44px", css_content)
        self.assertIn("min-height: 40px", css_content)
        # Check responsive cards media query
        self.assertIn("@media (max-width: 576px)", css_content)
        self.assertIn(".mobile-cards", css_content)

    def test_pages_have_responsive_wrappers_and_labels(self):
        pages = ["/dashboard", "/members", "/meals", "/bazar", "/deposits", "/settlement", "/reports", "/settings", "/about"]
        for page in pages:
            r = self.client.get(page)
            self.assertEqual(r.status_code, 200, f"Page {page} returned {r.status_code}")
            html = r.data.decode("utf-8")

            # Check meta viewport
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', html)
            # Verify no broken currency glyphs
            self.assertNotIn("\ufffd", html)
            # Verify no Bengali 'বাজার'
            self.assertNotIn("\u09ac\u09be\u099c\u09be\u09b0", html)

    def test_all_modals_have_csrf_tokens(self):
        pages = ["/members", "/bazar", "/deposits", "/settlement", "/settings"]
        for page in pages:
            r = self.client.get(page)
            html = r.data.decode("utf-8")
            # All POST forms must have csrf_token input
            forms = re.findall(r'<form[^>]*method=["\']post["\'][^>]*>', html, re.IGNORECASE)
            csrf_inputs = re.findall(r'<input[^>]*name=["\']csrf_token["\'][^>]*>', html)
            self.assertEqual(len(forms), len(csrf_inputs), f"Mismatch in POST forms vs CSRF inputs on {page}")


if __name__ == "__main__":
    unittest.main()
