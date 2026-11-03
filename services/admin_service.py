from datetime import datetime
from models import db
from models.mess import Mess
from models.user import User
from models.member import Member
from models.meal import Meal
from models.bazar import Bazar
from models.deposit import Deposit
from models.audit_log import AuditLog
from utils.currency import round_currency


class AdminService:
    @staticmethod
    def get_system_stats():
        """Compute application-wide high-level operational statistics."""
        total_messes = Mess.query.count()
        active_messes = Mess.query.filter_by(status="Active").count()
        suspended_messes = Mess.query.filter_by(status="Suspended").count()
        total_users = User.query.count()
        total_managers = User.query.filter_by(role="Manager").count()
        total_creators = User.query.filter_by(role="Creator").count()
        total_members = Member.query.count()
        total_meals = Meal.query.filter_by(taken=True).count()

        total_bazar = db.session.query(db.func.sum(Bazar.amount)).scalar() or 0.0
        total_deposits = db.session.query(db.func.sum(Deposit.amount)).scalar() or 0.0

        return {
            "total_messes": total_messes,
            "active_messes": active_messes,
            "suspended_messes": suspended_messes,
            "total_users": total_users,
            "total_managers": total_managers,
            "total_creators": total_creators,
            "total_members": total_members,
            "total_meals": total_meals,
            "total_bazar": round_currency(total_bazar),
            "total_deposits": round_currency(total_deposits),
        }

    @staticmethod
    def get_all_messes():
        """Retrieve all messes with aggregated operational metrics."""
        messes = Mess.query.order_by(Mess.id.asc()).all()
        result = []
        for m in messes:
            member_count = Member.query.filter_by(mess_id=m.id).count()
            user_count = User.query.filter_by(mess_id=m.id).count()
            meal_count = Meal.query.filter_by(mess_id=m.id, taken=True).count()
            bazar_sum = db.session.query(db.func.sum(Bazar.amount)).filter_by(mess_id=m.id).scalar() or 0.0
            deposit_sum = db.session.query(db.func.sum(Deposit.amount)).filter_by(mess_id=m.id).scalar() or 0.0

            result.append({
                "mess": m,
                "id": m.id,
                "name": m.name,
                "manager_name": m.manager_name,
                "status": getattr(m, "status", "Active"),
                "created_at": m.created_at,
                "member_count": member_count,
                "user_count": user_count,
                "meal_count": meal_count,
                "total_bazar": round_currency(bazar_sum),
                "total_deposits": round_currency(deposit_sum),
            })
        return result

    @staticmethod
    def toggle_mess_status(mess_id, admin_user=None, ip_address=None):
        """Toggle a mess's status between Active and Suspended."""
        mess = db.session.get(Mess, mess_id)
        if not mess:
            return False, "Mess not found."

        old_status = getattr(mess, "status", "Active")
        new_status = "Suspended" if old_status == "Active" else "Active"
        mess.status = new_status

        action = "SUSPEND_MESS" if new_status == "Suspended" else "ACTIVATE_MESS"
        admin_id = admin_user.id if admin_user else None
        admin_name = admin_user.username if admin_user else "System"

        AdminService.log_action(
            admin_id=admin_id,
            admin_username=admin_name,
            action=action,
            target_type="Mess",
            target_id=mess.id,
            target_name=mess.name,
            details=f"Mess '{mess.name}' (ID: {mess.id}) changed from {old_status} to {new_status}.",
            ip_address=ip_address
        )

        db.session.commit()
        return True, f"Mess '{mess.name}' is now {new_status}."

    @staticmethod
    def get_all_users():
        """Retrieve all users with their associated mess records."""
        return User.query.order_by(User.id.asc()).all()

    @staticmethod
    def reset_user_password(user_id, new_password, admin_user=None, ip_address=None):
        """Reset the password for any user/manager account."""
        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."

        clean_pass = (new_password or "").strip()
        if len(clean_pass) < 4:
            return False, "New password must be at least 4 characters long."

        user.set_password(clean_pass)

        admin_id = admin_user.id if admin_user else None
        admin_name = admin_user.username if admin_user else "System"
        mess_name = user.mess.name if user.mess else "N/A"

        AdminService.log_action(
            admin_id=admin_id,
            admin_username=admin_name,
            action="RESET_PASSWORD",
            target_type="User",
            target_id=user.id,
            target_name=user.username,
            details=f"Password reset for user '{user.username}' (Mess: {mess_name}).",
            ip_address=ip_address
        )

        db.session.commit()
        return True, f"Password for '{user.username}' was successfully reset."

    @staticmethod
    def change_user_role(user_id, new_role, admin_user=None, ip_address=None):
        """Change the role of a user (Creator, Manager, Member)."""
        valid_roles = ("Creator", "Manager", "Member")
        clean_role = (new_role or "").strip()
        if clean_role not in valid_roles:
            return False, f"Invalid role: '{new_role}'. Must be one of {', '.join(valid_roles)}."

        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found."

        # Safety check: Prevent demoting the last active Creator
        if user.role == "Creator" and clean_role != "Creator":
            creator_count = User.query.filter_by(role="Creator").count()
            if creator_count <= 1:
                return False, "Cannot demote the only Creator account in the system."

        old_role = user.role
        user.role = clean_role

        admin_id = admin_user.id if admin_user else None
        admin_name = admin_user.username if admin_user else "System"

        AdminService.log_action(
            admin_id=admin_id,
            admin_username=admin_name,
            action="CHANGE_ROLE",
            target_type="User",
            target_id=user.id,
            target_name=user.username,
            details=f"Role for '{user.username}' changed from {old_role} to {clean_role}.",
            ip_address=ip_address
        )

        db.session.commit()
        return True, f"Role for '{user.username}' updated to {clean_role}."

    @staticmethod
    def log_action(admin_id, admin_username, action, target_type, target_id=None, target_name=None, details=None, ip_address=None):
        """Record an administrative action to the AuditLog."""
        log = AuditLog(
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            details=details,
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        return log

    @staticmethod
    def get_audit_logs(limit=100):
        """Retrieve recent administrative audit logs."""
        return AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
