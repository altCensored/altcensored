from flask import (
    Blueprint, redirect, request, current_app, session, render_template, flash, url_for
)
from sqlalchemy.orm.exc import NoResultFound
from flask_babelplus import lazy_gettext
from .database import db_session
from .models import User
from werkzeug.security import check_password_hash, generate_password_hash

from . import util
from .util import ( 
    get_locale, get_theme, get_navtabs, get_navtabs_index, send_welcome_email, 
    send_forgot_password_email, generate_confirmation_token, confirm_token, login_required
    )
import datetime
from email_validator import validate_email, EmailNotValidError

bp = Blueprint('auth', __name__, url_prefix='/auth')


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
    return check_password_hash(user.password, password)


def validate_user_email(email):
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return e


def register_user(email, password): 
    if session.get('locale') is None:
        get_locale()
    if session.get('theme') is None:
        session['theme'] = get_theme()
    if session.get('navtabs') is None:
        get_navtabs()
    if session.get('navtabs_index') is None:
        get_navtabs_index()

    d = datetime.date.today()
    dt = datetime.datetime.now(tz=None)

    user = User (
        email=email, password=generate_password_hash(password), created_date=d, updated=dt, email_verified=False,
        locale = session['locale'], theme = session['theme'], 
        navtabs =  [ session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3'] ], 
        navtabs_index =  [ session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3'] ], 
        )
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
@bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        submitvalue = request.form['submitvalue']
        ret_val = validate_user_email(email)
        if ret_val is not None:
            flash(str(ret_val), 'error')
            return redirect(url_for('auth.login'))
        if user_and_password_is_valid(email, password):
            user = db_session.query(User).filter(User.email==email).one()
            session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, public=user.public, email_verified=user.email_verified)
            session['locale'] = user.locale
            session['theme'] = user.theme

            session['navtabs']['navtab1'] = user.navtabs[0]
            session['navtabs']['navtab2'] = user.navtabs[1]
            session['navtabs']['navtab3'] = user.navtabs[2]

            session['navtabs_index']['navtab1'] = user.navtabs_index[0]
            session['navtabs_index']['navtab2'] = user.navtabs_index[1]
            session['navtabs_index']['navtab3'] = user.navtabs_index[2]

            if user.username is None and not user.email_verified:
                send_confirm_email(email)
                flash('Choose Username. Account not verified. Confirmation email resent', 'success')
                return redirect(url_for('settings.index'))
            elif user.username is None:
                flash('Choose Username', 'success')
                return redirect(url_for('settings.index'))
            elif not user.email_verified:
                send_confirm_email(email)
                flash('Account not verified. Confirmation email resent', 'success')
            else:
                flash('You were successfully logged in', 'success')
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
            session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, public=user.public, email_verified=user.email_verified)
            flash('Now Choose Username, Confirmation email sent', 'success')
            return redirect(url_for('settings.index'))

        elif submitvalue == 'reset':
            if not user_exists(email):
                flash('User does not exist', 'error')
                return redirect(url_for('auth.login'))
            send_reset_password_email(email)
            flash('Reset password email sent', 'success')
            return redirect(url_for('video.index'))

        else:
            flash('Email and password combination is invalid', 'error')
    return render_template('/auth/auth_index.html')


@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    email = confirm_token(token)
    if email == False:
        flash('The confirmation link is invalid or has expired', 'danger')
        return redirect(url_for('video.index'))
    user = db_session.query(User).filter(User.email==email).one()
    if user.email_verified:
        session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, public=user.public, email_verified=user.email_verified)
        flash('Account already confirmed. Please login', 'success')
        return redirect(url_for('video.index'))
    else:
        user.email_verified = True
        user.email_verified_date = datetime.date.today()
        user.updated = datetime.datetime.now(tz=None)
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
@login_required
def logout():
    user = db_session.query(User).filter(User.email == session['user']['email']).one()
    user.updated = datetime.datetime.now(tz=None)
    user.locale = session['locale']
    user.theme = session['theme'] 
    user.navtabs =  [ session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3'] ]
    user.navtabs_index =  [ session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3'] ]
    db_session.commit()
    
    flash('Logout complete', 'success')
    session['user'] = None
    return redirect(url_for('video.index'))


@bp.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    user_id = session['user']['id']
    user_email = session['user']['email']
    l_msg = lazy_gettext('Delete User ')
    item_quoted = (f'"{user_email}"')
    message = l_msg + ' ' + item_quoted + '?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(User.id == user_id).one()
            db_session.delete(user)
            db_session.commit()
            flash(item_quoted + ' deleted', 'success')
            session['user'] = None
            return redirect(url_for('video.index'))
        else:
            flash(item_quoted + ' NOT deleted', 'error')
            return redirect(url_for('video.index'))
    return render_template('widgets/widgets_confirm.html', message=message)