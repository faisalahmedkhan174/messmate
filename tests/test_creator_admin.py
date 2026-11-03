import unittest
from app import create_app
from models import db
from models.mess import Mess
from models.user import User
from models.audit_log import AuditLog
from services.admin_service import AdminService


class CreatorAdminTestCase(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret-creator-admin"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create Alpha Mess (Active)
        self.mess_alpha = Mess(name="Alpha Mess", manager_name="Alpha Manager", status="Active")
        db.session.add(self.mess_alpha)
        db.session.flush()

        # Manager user for Alpha Mess
        self.manager_user = User(
            mess_id=self.mess_alpha.id,
            username="alphamanager",
            manager_name="Alpha Manager",
            role="Manager"
        )
        self.manager_user.set_password("manager123")
        db.session.add(self.manager_user)

        # Creator / Super Admin user
        self.creator_user = User(
            mess_id=self.mess_alpha.id,
            username="systemcreator",
            manager_name="System Creator",
            role="Creator"
        )
        self.creator_user.set_password("creator123")
        db.session.add(self.creator_user)

        # Member user (read-only / member)
        self.member_user = User(
            mess_id=self.mess_alpha.id,
            username="normalmember",
            manager_name="Normal Member",
            role="Member"
        )
        self.member_user.set_password("member123")
        db.session.add(self.member_user)

        # Create Beta Mess
        self.mess_beta = Mess(name="Beta Mess", manager_name="Beta Manager", status="Active")
        db.session.add(self.mess_beta)
        db.session.flush()

        self.beta_manager = User(
            mess_id=self.mess_beta.id,
            username="betamanager",
            manager_name="Beta Manager",
            role="Manager"
        )
        self.beta_manager.set_password("betapass")
        db.session.add(self.beta_manager)

        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, user, mess):
        """Simulate authentication session for a given user and mess."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["mess_id"] = mess.id
            sess["manager_name"] = user.manager_name
            sess["mess_name"] = mess.name
            sess["role"] = user.role
            sess["is_creator"] = user.is_creator

    # 1. Unauthenticated Access
    def test_unauthenticated_admin_access_redirects_to_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        response2 = self.client.get("/admin/audit-logs")
        self.assertEqual(response2.status_code, 302)
        self.assertIn("/login", response2.headers["Location"])

    # 2. Manager Access Forbidden (403)
    def test_manager_access_to_admin_returns_403(self):
        self.login_as(self.manager_user, self.mess_alpha)

        # Accessing dashboard
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 403)

        # Accessing audit logs
        response_logs = self.client.get("/admin/audit-logs")
        self.assertEqual(response_logs.status_code, 403)

        # Trying to POST to toggle mess status
        response_post = self.client.post(f"/admin/messes/{self.mess_beta.id}/toggle-status")
        self.assertEqual(response_post.status_code, 403)

    # 3. Member Access Forbidden (403)
    def test_member_access_to_admin_returns_403(self):
        self.login_as(self.member_user, self.mess_alpha)

        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 403)

    # 4. Creator Access Allowed (200)
    def test_creator_access_to_admin_returns_200(self):
        self.login_as(self.creator_user, self.mess_alpha)

        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Creator Control Center", response.data)
        self.assertIn(b"Alpha Mess", response.data)
        self.assertIn(b"Beta Mess", response.data)
        self.assertIn(b"alphamanager", response.data)

    # 5. Suspend and Reactivate Mess
    def test_creator_can_suspend_and_reactivate_mess(self):
        self.login_as(self.creator_user, self.mess_alpha)

        # Toggle to Suspended
        response = self.client.post(f"/admin/messes/{self.mess_beta.id}/toggle-status", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Verify DB status
        beta_mess = db.session.get(Mess, self.mess_beta.id)
        self.assertEqual(beta_mess.status, "Suspended")

        # Verify AuditLog entry
        log = AuditLog.query.filter_by(action="SUSPEND_MESS", target_id=self.mess_beta.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin_username, "systemcreator")

        # Toggle back to Active
        response2 = self.client.post(f"/admin/messes/{self.mess_beta.id}/toggle-status", follow_redirects=True)
        self.assertEqual(response2.status_code, 200)
        db.session.refresh(beta_mess)
        self.assertEqual(beta_mess.status, "Active")

        log2 = AuditLog.query.filter_by(action="ACTIVATE_MESS", target_id=self.mess_beta.id).first()
        self.assertIsNotNone(log2)

    # 6. Suspended Mess Blocks Manager Login
    def test_suspended_mess_blocks_manager_login(self):
        # Suspend beta mess
        self.mess_beta.status = "Suspended"
        db.session.commit()

        # Manager tries to log in to suspended mess
        response = self.client.post("/login", data={
            "mess_name": "Beta Mess",
            "username": "betamanager",
            "password": "betapass"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This mess has been suspended", response.data)

        # Ensure session was not created
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    # 7. Suspended Mess Blocks Active Manager Session
    def test_suspended_mess_blocks_active_manager_session(self):
        # Log in to Beta Mess
        self.login_as(self.beta_manager, self.mess_beta)

        # Admin suspends beta mess in background
        self.mess_beta.status = "Suspended"
        db.session.commit()

        # Beta manager tries to access dashboard
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This mess has been suspended", response.data)

        # Session must have been cleared
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    # 8. Reset Manager Password
    def test_creator_can_reset_manager_password(self):
        self.login_as(self.creator_user, self.mess_alpha)

        new_password = "newsecretpassword456"
        response = self.client.post(f"/admin/users/{self.beta_manager.id}/reset-password", data={
            "new_password": new_password
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Verify manager can login with new password
        login_res = self.client.post("/login", data={
            "mess_name": "Beta Mess",
            "username": "betamanager",
            "password": new_password
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Welcome back", login_res.data)

        # Verify audit log
        log = AuditLog.query.filter_by(action="RESET_PASSWORD", target_id=self.beta_manager.id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin_username, "systemcreator")

    # 9. Change User Role
    def test_creator_can_change_user_role(self):
        self.login_as(self.creator_user, self.mess_alpha)

        response = self.client.post(f"/admin/users/{self.member_user.id}/change-role", data={
            "role": "Manager"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        user = db.session.get(User, self.member_user.id)
        self.assertEqual(user.role, "Manager")

        # Verify demoting only creator is prevented
        response2 = self.client.post(f"/admin/users/{self.creator_user.id}/change-role", data={
            "role": "Manager"
        }, follow_redirects=True)
        self.assertEqual(response2.status_code, 200)
        self.assertIn(b"Cannot demote the only Creator", response2.data)

        creator = db.session.get(User, self.creator_user.id)
        self.assertEqual(creator.role, "Creator")

    # 10. Switch Mess Context
    def test_creator_can_switch_mess_view(self):
        self.login_as(self.creator_user, self.mess_alpha)

        response = self.client.post(f"/admin/switch-mess/{self.mess_beta.id}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("mess_id"), self.mess_beta.id)
            self.assertEqual(sess.get("mess_name"), "Beta Mess")

    # 11. Public Register Never Creates Creator
    def test_public_register_never_creates_creator(self):
        response = self.client.post("/register", data={
            "mess_name": "New Public Mess",
            "manager_name": "Public Manager",
            "username": "publicuser",
            "password": "password123",
            "confirm_password": "password123",
            "role": "Creator"  # Tampered field
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(username="publicuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "Manager")
        self.assertFalse(user.is_creator)

    # 12. Audit Logs View
    def test_audit_logs_view(self):
        self.login_as(self.creator_user, self.mess_alpha)

        AdminService.log_action(
            admin_id=self.creator_user.id,
            admin_username=self.creator_user.username,
            action="SECURITY_TEST_EVENT",
            target_type="System",
            details="Automated security event test."
        )
        db.session.commit()

        response = self.client.get("/admin/audit-logs")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SECURITY_TEST_EVENT", response.data)
        self.assertIn(b"systemcreator", response.data)


if __name__ == "__main__":
    unittest.main()
