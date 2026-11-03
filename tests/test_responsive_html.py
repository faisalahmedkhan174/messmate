import unittest
import os

from app import create_app
from models import db
from models.mess import Mess
from models.user import User


class ResponsiveAndHTMLTestCase(unittest.TestCase):
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

        # Create mess and user for authenticated requests
        self.mess = Mess(name="Green Mess", manager_name="Manager Alex")
        db.session.add(self.mess)
        db.session.flush()
        self.user = User(mess_id=self.mess.id, username="alex", manager_name="Manager Alex")
        self.user.set_password("pass123")
        db.session.add(self.user)
        db.session.commit()

        # Login session
        with self.client.session_transaction() as sess:
            sess["mess_id"] = self.mess.id
            sess["user_id"] = self.user.id
            sess["mess_name"] = self.mess.name
            sess["manager_name"] = self.user.manager_name

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_viewport_meta_tag_present_in_base(self):
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode("utf-8")
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', html)

    def test_no_bengali_bazar_label_in_html(self):
        urls = ["/dashboard", "/members", "/meals", "/bazar", "/deposits", "/settlement", "/reports", "/settings", "/about"]
        for url in urls:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, f"Failed on {url}")
            html = r.data.decode("utf-8")
            self.assertNotIn("\u09ac\u09be\u099c\u09be\u09b0", html, f"Found Bengali 'বাজার' in {url}")
            self.assertNotIn("\ufffd", html, f"Found broken glyph \\ufffd in {url}")

    def test_creator_image_asset_integrity(self):
        # 1. Image exists in static directory
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
        creator_img_path = os.path.join(static_dir, "creator.jpg")
        self.assertTrue(os.path.exists(creator_img_path), "creator.jpg must exist in static/")
        self.assertGreater(os.path.getsize(creator_img_path), 1000, "creator.jpg must have non-zero file size")

        # 2. Check About page references it
        r = self.client.get("/about")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode("utf-8")
        self.assertIn("creator.jpg", html)
        self.assertIn("Faisal Ahmed Khan", html)

    def test_custom_404_error_page(self):
        r = self.client.get("/non-existent-page-12345")
        self.assertEqual(r.status_code, 404)
        html = r.data.decode("utf-8")
        self.assertIn("Page Not Found", html)
        self.assertIn("404", html)


if __name__ == "__main__":
    unittest.main()
