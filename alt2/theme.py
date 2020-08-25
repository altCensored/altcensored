from flask import (
    Blueprint, redirect, session, request
)

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
    return redirect(request.args.get('original_url', '/'))