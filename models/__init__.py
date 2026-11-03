from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .mess import Mess          # noqa: E402,F401
from .user import User          # noqa: E402,F401
from .member import Member      # noqa: E402,F401
from .meal import Meal          # noqa: E402,F401
from .bazar import Bazar        # noqa: E402,F401
from .deposit import Deposit    # noqa: E402,F401
from .audit_log import AuditLog  # noqa: E402,F401
