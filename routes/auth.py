from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import db
from models.mess import Mess
from models.user import User

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        mess_name = (request.form.get("mess_name") or "").strip()
        manager_name = (request.form.get("manager_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        errors = []
        if not mess_name:
            errors.append("Mess/Hostel name is required.")
        if not manager_name:
            errors.append("Manager name is required.")
        if not username:
            errors.append("Username is required.")
        if not password:
            errors.append("Password is required.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if len(password) < 4 and password:
            errors.append("Password should be at least 4 characters.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", form=request.form)

        try:
            mess = Mess(name=mess_name, manager_name=manager_name)
            db.session.add(mess)
            db.session.flush()  # get mess.id

            user = User(mess_id=mess.id, username=username, manager_name=manager_name,
                        role="Manager")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not create account. Username may already exist for this mess name, "
                  "or a server error occurred.", "danger")
            return render_template("register.html", form=request.form)

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mess_name = (request.form.get("mess_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        mess = Mess.query.filter(db.func.lower(Mess.name) == mess_name.lower()).first()
        user = None
        if mess:
            user = User.query.filter_by(mess_id=mess.id, username=username).first()

        if not mess or not user or not user.check_password(password):
            flash("Invalid mess name, username, or password.", "danger")
            return render_template("login.html", form=request.form)

        # Check if mess is suspended (Creators can still login to inspect)
        if getattr(mess, "status", "Active") == "Suspended" and not user.is_creator:
            flash("This mess has been suspended by the administrator. Please contact support.", "danger")
            return render_template("login.html", form=request.form)

        session.clear()
        session["mess_id"] = mess.id
        session["user_id"] = user.id
        session["manager_name"] = user.manager_name
        session["mess_name"] = mess.name
        session["role"] = user.role
        session["is_creator"] = user.is_creator

        if user.is_creator:
            flash("Welcome back, Creator {}!".format(user.manager_name), "success")
        else:
            flash("Welcome back, {}!".format(user.manager_name), "success")
        return redirect(url_for("dashboard.index"))

    return render_template("login.html", form={})


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
