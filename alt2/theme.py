from flask import (
    Blueprint, redirect, session, request, abort
)
from . import config

bp = Blueprint('theme', __name__, url_prefix='/theme' )
url_orig = config.RANDOM_VALUE


@bp.route('/toggle', methods=['GET'])
def toggle():
    if 'theme' in session:
        if session['theme'] == 'light':
            session['theme'] = 'dark'
        else:
            session['theme'] = 'light'
    else:
        session['theme'] = 'dark'

    if (request.args.get(url_orig)):
        if "//" in (request.args.get(url_orig)):
            abort(404)

    return redirect(request.args.get(url_orig, '/'))
