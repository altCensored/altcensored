from flask import (
    Blueprint, redirect, session, request, abort
)

bp = Blueprint('theme', __name__, url_prefix='/theme' )


@bp.route('/toggle', methods=['GET'])
def toggle():
    try:
        if "http" in (request.args.get('original_url')):
            abort(404)

    finally:
        if 'theme' in session:
            if session['theme'] == 'light':
                session['theme'] = 'dark'
            else:
                session['theme'] = 'light'
        else:
            session['theme'] = 'dark'

    return redirect(request.args.get('original_url', '/'))
