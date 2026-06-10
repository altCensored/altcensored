from flask import (
    Blueprint, redirect, session, request, abort
)
from urllib.parse import unquote_plus

bp = Blueprint('theme', __name__, url_prefix='/theme' )

@bp.route('/toggle', methods=['POST'])
def toggle():
    if 'theme' in session:
        if session['theme'] == 'light':
            session['theme'] = 'dark'
        else:
            session['theme'] = 'light'
    else:
        session['theme'] = 'dark'

    redir = unquote_plus(request.form.get('redir', '/'))
    if not redir.startswith('/') or redir.startswith('//'):
        abort(404)

    return redirect(redir)
