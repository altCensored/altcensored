from flask import (
    Blueprint, redirect, session, request, abort
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

#    try:
#        if "//" in (request.args.get('original_url2')):
#            abort(404)
#    except:
#        pass

    if (request.args.get('original_url2')):
        if "//" in (request.args.get('original_url2')):
            abort(404)

    return redirect(request.args.get('original_url2', '/'))
