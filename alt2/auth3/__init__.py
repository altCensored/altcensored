from flask import Blueprint

bp = Blueprint('auth3', __name__)

from alt2.auth3 import routes
