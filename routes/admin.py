from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.security import creator_required, current_user
from services.admin_service import AdminService
from models import db
from models.mess import Mess

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@creator_required
def check_creator_access():
    """Double-layer protection ensuring only Creator role accounts can access any admin endpoint."""
    pass


@bp.route("/")
@creator_required
def index():
    """Main Creator/Super Admin control dashboard."""
    stats = AdminService.get_system_stats()
    messes = AdminService.get_all_messes()
    users = AdminService.get_all_users()
    recent_audit_logs = AdminService.get_audit_logs(limit=15)
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        messes=messes,
        users=users,
        audit_logs=recent_audit_logs,
    )


@bp.route("/messes/<int:mess_id>/toggle-status", methods=["POST"])
@creator_required
def toggle_mess_status(mess_id):
    """Suspend or reactivate a mess."""
    admin_user = current_user()
    ip_addr = request.remote_addr
    success, msg = AdminService.toggle_mess_status(mess_id, admin_user=admin_user, ip_address=ip_addr)
    flash(msg, "success" if success else "danger")
    return redirect(url_for("admin.index"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@creator_required
def reset_user_password(user_id):
    """Reset a user or manager account password."""
    new_password = request.form.get("new_password", "")
    admin_user = current_user()
    ip_addr = request.remote_addr
    success, msg = AdminService.reset_user_password(user_id, new_password, admin_user=admin_user, ip_address=ip_addr)
    flash(msg, "success" if success else "danger")
    return redirect(url_for("admin.index"))


@bp.route("/users/<int:user_id>/change-role", methods=["POST"])
@creator_required
def change_user_role(user_id):
    """Promote or modify account role (Creator / Manager / Member)."""
    new_role = request.form.get("role", "")
    admin_user = current_user()
    ip_addr = request.remote_addr
    success, msg = AdminService.change_user_role(user_id, new_role, admin_user=admin_user, ip_address=ip_addr)
    flash(msg, "success" if success else "danger")
    return redirect(url_for("admin.index"))


@bp.route("/audit-logs")
@creator_required
def audit_logs():
    """Full administrative audit logs view."""
    logs = AdminService.get_audit_logs(limit=200)
    return render_template("admin/audit_logs.html", audit_logs=logs)


@bp.route("/switch-mess/<int:mess_id>", methods=["GET", "POST"])
@creator_required
def switch_mess(mess_id):
    """Allow Creator to switch active mess context to inspect mess data."""
    mess = db.session.get(Mess, mess_id)
    if not mess:
        flash("Target mess not found.", "danger")
        return redirect(url_for("admin.index"))

    session["mess_id"] = mess.id
    session["mess_name"] = mess.name
    admin_user = current_user()
    if admin_user:
        AdminService.log_action(
            admin_id=admin_user.id,
            admin_username=admin_user.username,
            action="SWITCH_MESS_CONTEXT",
            target_type="Mess",
            target_id=mess.id,
            target_name=mess.name,
            details=f"Creator switched active context to mess '{mess.name}'.",
            ip_address=request.remote_addr
        )
        db.session.commit()

    flash(f"Switched active view to: {mess.name}", "info")
    return redirect(url_for("dashboard.index"))
