from flask import (Blueprint, redirect)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login')
def login():
    return redirect('/')
