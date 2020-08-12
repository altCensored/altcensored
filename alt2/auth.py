from flask import (Blueprint, redirect, request, current_app, session, render_template, flash, url_for)
from sqlalchemy.orm.exc import NoResultFound

from .database import db_session
from .models import User
import bcrypt
from .util import send_email, generate_confirmation_token

bp = Blueprint('auth', __name__, url_prefix='/auth')

salt = bcrypt.gensalt()


def find_user_by_email(email):
    try:
        return db_session.query(User).filter(User.email == email).one()
    except NoResultFound:
        return None


def user_exists(email):
    return find_user_by_email(email) is not None


def user_and_password_is_valid(email, password):
    user = find_user_by_email(email)
    if not user:
        print("Could not find user", email)
        return False
    return bcrypt.checkpw(password.encode('utf8'), user.password.encode('utf8'))


def register_user(email, password):
    user = User(email=email, password=bcrypt.hashpw(password.encode('utf8'), salt).decode('utf8'))

    token = generate_confirmation_token(email)
    confirm_url = url_for('subscription.index', token=token, _external=True)
    html = render_template('subscription/activate.html', confirm_url=confirm_url)
    send_email(email,html)

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    if user_and_password_is_valid(email, password):
        user = db_session.query(User).filter(User.email==email).one()
        session['user'] = dict(id=user.id, email=user.email)
        flash('You were successfully logged in', 'success')
        return redirect('/')
    else:
        flash('Email and password combination are invalid', 'error')
        return redirect('/')


@bp.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    password = request.form['password']
    if user_exists(email):
        flash('User already exists', 'error')
        return redirect('/')
    else:
        user = register_user(email, password)
        session['user'] = dict(id=user.id, email=user.email)
        flash('Registration complete', 'success')
        return redirect('/')


@bp.route('/logout')
def logout():
    session['user'] = None
    flash('Logout complete', 'success')
    return redirect('/')


@bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    flash('A reset link will be sent to your email address.', 'success')
    return redirect('/')
