from flask import (
    Blueprint, redirect, session, request, abort
)
from .util import get_videocount

bp = Blueprint('theme', __name__, url_prefix='/theme' )

@bp.route('/toggle', methods=['GET'])
def toggle():
    if 'theme' in session:
        if session['theme'] == 'light':
            session['theme'] = 'dark'
        else:
            session['theme'] = 'light'
    else:
        session['theme'] = 'dark'

    get_videocount()

    if (request.args.get(session['videocount'])):
        if "//" in (request.args.get(session['videocount'])):
            abort(404)

    return redirect(request.args.get(session['videocount'], '/'))
