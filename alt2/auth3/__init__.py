from flask import Blueprint

bp = Blueprint('auth', __name__)

from alt2.auth3 import routes
