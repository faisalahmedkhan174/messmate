import unittest
from app import create_app
from models import db
from models.mess import Mess
from models.user import User
from models.member import Member
from services.member_service import MemberService


class SecurityAndIsolationTestCase(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = False  # To test live CSRF & auth filters
            SECRET_KEY = "test-secret-security"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Mess 1
        self.mess1 = Mess(name="Mess Alpha", manager_name="Manager 1")
        db.session.add(self.mess1)
        db.session.flush()
        self.user1 = User(mess_id=self.mess1.id, username="alpha_user", manager_name="Manager 1")
        self.user1.set_password("pass123")
        db.session.add(self.user1)

        # Mess 2
        self.mess2 = Mess(name="Mess Beta", manager_name="Manager 2")
        db.session.add(self.mess2)
        db.session.flush()
        self.user2 = User(mess_id=self.mess2.id, username="beta_user", manager_name="Manager 2")
        self.user2.set_password("pass456")
        db.session.add(self.user2)

        # Member belonging to Mess 1
        self.mem1 = Member(mess_id=self.mess1.id, name="Alpha Member", status="Active")
        db.session.add(self.mem1)

        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_unauthenticated_access_redirects_to_login(self):
        protected_urls = ["/", "/dashboard", "/members", "/meals", "/bazar", "/deposits", "/settlement", "/reports", "/settings"]
        for url in protected_urls:
            r = self.client.get(url, follow_redirects=False)
            self.assertEqual(r.status_code, 302, f"Expected redirect for unauthenticated {url}")
            self.assertIn("/login", r.headers["Location"])

    def test_csrf_protection_rejects_missing_token_on_post(self):
        # Login to Mess 1
        with self.client.session_transaction() as sess:
            sess["mess_id"] = self.mess1.id
            sess["user_id"] = self.user1.id
            sess["_csrf_token"] = "valid-token-12345"

        # Try POST without csrf_token -> Should be 400 Bad Request
        r = self.client.post("/members/add", data={"name": "Hacker Member"})
        self.assertEqual(r.status_code, 400)

        # Try POST with valid csrf_token -> Should succeed (302 redirect to members)
        r2 = self.client.post("/members/add", data={"name": "Valid Member", "csrf_token": "valid-token-12345"})
        self.assertEqual(r2.status_code, 302)

    def test_cross_mess_data_isolation(self):
        # Login as Mess 2 manager
        with self.client.session_transaction() as sess:
            sess["mess_id"] = self.mess2.id
            sess["user_id"] = self.user2.id
            sess["_csrf_token"] = "valid-token-beta"

        # Mess 2 manager tries to view Mess 1's member details -> 404
        r = self.client.get(f"/members/{self.mem1.id}/details")
        self.assertEqual(r.status_code, 404)

        # Mess 2 manager tries to edit Mess 1's member -> 404
        r2 = self.client.post(
            f"/members/{self.mem1.id}/edit",
            data={"name": "Tampered Name", "csrf_token": "valid-token-beta"}
        )
        self.assertEqual(r2.status_code, 404)

        # Verify member name remains unchanged in database
        check_mem = db.session.get(Member, self.mem1.id)
        self.assertEqual(check_mem.name, "Alpha Member")


if __name__ == "__main__":
    unittest.main()
