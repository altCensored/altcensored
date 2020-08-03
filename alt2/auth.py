from flask import (Blueprint, redirect, request, current_app, session)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    session['logged_in'] = True
    return redirect('/')


@bp.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    return redirect('/')