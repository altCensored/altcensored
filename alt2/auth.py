from flask import (
    Blueprint, redirect, request, current_app, session, render_template, flash, url_for
)
from sqlalchemy.orm.exc import NoResultFound
from .database import db_session
from .models import User
import bcrypt
from . import util
from .util import get_locale, send_welcome_email, send_forgot_password_email, generate_confirmation_token, confirm_token
import functools

bp = Blueprint('auth', __name__, url_prefix='/auth')

salt = bcrypt.gensalt()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view


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
        return False
    return bcrypt.checkpw(password.encode('utf8'), user.password.encode('utf8'))


def register_user(email, password):
    user = User(email=email, password=bcrypt.hashpw(password.encode('utf8'), salt).decode('utf8'), email_verified=False)
    db_session.add(user)
    db_session.commit()
    return user


def send_confirm_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    html = render_template('auth/auth_activate.html', confirm_url=confirm_url)
    send_welcome_email(email, html)


def send_reset_password_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.reset_password', token=token, _external=True)
    html = render_template('auth/auth_forgot_password_email.html', confirm_url=confirm_url)
    send_forgot_password_email(email, html)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        submitvalue = request.form['submitvalue']
        if user_and_password_is_valid(email, password):
            user = db_session.query(User).filter(User.email==email).one()
            session['user'] = dict(id=user.id, email=user.email)
            if user.email_verified:
                flash('You were successfully logged in', 'success')
                return redirect(url_for('video.index'))
            else:
                send_confirm_email(email)
                flash('Account not verified. Confirmation email resent', 'success')
                return redirect(url_for('video.index'))
        elif submitvalue == 'register':
            if not password:
                flash('Enter Password', 'error')
                return redirect(url_for('auth.login'))
            if user_exists(email):
                flash('User already exists', 'error')
                return redirect(url_for('auth.login'))
            user = register_user(email, password)
            send_confirm_email(email)
            session['user'] = dict(id=user.id, email=user.email)
            flash('Confirmation email sent', 'success')
            return redirect(url_for('video.index'))
        elif submitvalue == 'reset':
            send_reset_password_email(email)
            flash('Reset password email sent', 'success')
            return redirect(url_for('video.index'))
        else:
            flash('Email and password combination is invalid', 'error')
    return render_template('/auth/auth_index.html', locale=util.get_locale())



@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    email = confirm_token(token)
    if email == False:
        flash('The confirmation link is invalid or has expired', 'danger')
        return redirect(url_for('video.index'))
    user = db_session.query(User).filter(User.email==email).one()
    if user.email_verified:
        session['user'] = dict(id=user.id, email=user.email, )
        flash('Account already confirmed. Please login', 'success')
        return redirect(url_for('video.index'))
    else:
        user.email_verified = True
        db_session.add(user)
        db_session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('video.index'))


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token)
    if email == False:
        flash('The reset password link is invalid or has expired', 'danger')
        return redirect(url_for('video.index'))
    if request.method == 'GET':
        return render_template('auth/auth_reset_password.html', locale=util.get_locale(), token=token)
    elif request.method == 'POST':
        password = request.form['password']
        db_session.query(User).filter(User.email == email).update({"password": bcrypt.hashpw(password.encode('utf8'), salt).decode('utf8')})
        db_session.commit()
        flash('Password has been updated', 'success')
        return redirect(url_for('video.index'))


@bp.route('/logout')
def logout():
    session['user'] = None
    flash('Logout complete', 'success')
    return redirect(url_for('video.index'))