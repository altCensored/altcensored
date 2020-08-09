from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    send_from_directory, make_response, session, current_app )
from . import util

bp = Blueprint('subscription', __name__, url_prefix='/subscription')


@bp.route('/')
def index():
    return render_template('subscription/subscription_index.html', locale=util.get_locale())