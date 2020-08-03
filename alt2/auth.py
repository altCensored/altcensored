from flask import (Blueprint, redirect, request, current_app, session)

from .database import db_session
from .models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    try:
        user = db_session.query(User).filter(User.email==email).one()
        session['logged_in'] = True
        return redirect('/')
    except:
        return redirect('/?unable-to-login=true')


@bp.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    return redirect('/')


@bp.route('/logout', methods=['POST'])
def logout():
    session['logged_in'] = False
    return redirect('/')