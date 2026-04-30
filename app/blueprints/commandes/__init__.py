from flask import Blueprint

commandes_bp = Blueprint('commandes', __name__)

from . import routes  # noqa: E402, F401