from flask import Blueprint

catalogue_bp = Blueprint('catalogue', __name__)

from . import routes  # noqa: E402, F401