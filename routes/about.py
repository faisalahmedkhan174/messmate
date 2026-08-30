from flask import Blueprint, render_template

from .helpers import login_required

bp = Blueprint("about", __name__)


@bp.route("/about")
@login_required
def index():
    return render_template("about.html")
