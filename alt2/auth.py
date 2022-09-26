import datetime
import json
from datetime import timezone
from flask import (
    Blueprint, redirect, request, session, render_template, flash, url_for
)
from flask_babelplus import lazy_gettext
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash, generate_password_hash

from . import util
from .database import db_session
from .models import User
from .util import (
    get_locale, get_theme, get_navtabs, get_navtabs_index,
    send_forgot_password_email, generate_confirmation_token, confirm_token, email_exists, validate_user_email,
    login_required, generate_random, create_captcha, set_session, send_confirm_email
)

bp = Blueprint('auth', __name__, url_prefix='/auth')

def find_user_by_email(email):
    try:
        return db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    except NoResultFound:
        return None


def generate_captcha():
    session['myrandom'] = generate_random()
    session['mycaptcha'] = 'captcha_tmp.png'
    create_captcha(session['myrandom'], session['mycaptcha'])


def user_and_password_is_valid(email, password):
    user = find_user_by_email(email)
    if not user:
        return False
    return check_password_hash(user.password, password)


def username_exist(username):
    if username is None:
        return False
    if db_session.query(User.username).filter(func.lower(User.username) == func.lower(username)).scalar() is not None:
        return True


def register_user(email, password, username):
    now = datetime.datetime.now(timezone.utc)
    email_lastsent_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(30)

    settings = {
        "theme": session['theme'],
        "locale": session['locale'],
        "playnext": session['playnext'],
        "looplist": session['looplist']
    }

    user = User (
        email=email.lower(), password=generate_password_hash(password), username=username, description="", created_date=now, \
        updated=now, email_lastsent_date=email_lastsent_date, email_verified=False, view_counter = 0, \
        navtabs=[ session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3'] ], \
        settings=settings, \
        navtabs_index=[ session['navtabs_index']['navtab1'],session['navtabs_index']['navtab2'],session['navtabs_index']['navtab3'] ],
    )
    db_session.add(user)
    db_session.commit()
    return user


def send_reset_password_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.reset_password', token=token, _external=True)
    html = render_template('auth/auth_forgot_password_email.html', confirm_url=confirm_url)
    send_forgot_password_email(email, html)


@bp.route('/login', methods=['GET', 'POST'])
@bp.route('/', methods=['GET', 'POST'])
def login():
#    set_session()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        submitvalue = request.form['submitvalue']
        ret_val = validate_user_email(email)
        try:
            username = request.form['username']
        except:
            username = None

        if ret_val is not None:
            flash(str(ret_val), 'error')
            return redirect(url_for('auth.login'))

        if submitvalue == 'reset':
            if not email_exists(email):
                no_user = lazy_gettext('User does not exist')
                flash(no_user, 'error')
                return redirect(url_for('auth.login'))
            send_reset_password_email(email)
            reset_pw = lazy_gettext('Reset password email sent')
            flash(reset_pw, 'success')
            return redirect(url_for('video.index'))

        if submitvalue == 'clear':
            session['register_email'] = None
            clear_text = lazy_gettext('Try again')
            flash(clear_text, 'success')
            return redirect(url_for('auth.login'))

        if not email_exists(email) and session.get('register_email') is None:
            session['register_email'] = email
            generate_captcha()
            return redirect(url_for('auth.login'))

        if username_exist(username):
            session['register_email'] = email
            user_does_exist = lazy_gettext('Username exists')
            flash(user_does_exist, 'error')
            return redirect(url_for('auth.login'))

        if submitvalue == 'register':
            captcha = request.form['captcha']
            if captcha.casefold() != session['myrandom'].casefold():
                generate_captcha()
                captcha_wrong = lazy_gettext('Captcha not correct')
                flash(captcha_wrong, 'error')
                return redirect(url_for('auth.login'))

            if util.contains_profanity(username):
                flash(no_profanity, 'error')
                return redirect(url_for('auth.login'))

            if email_exists(email):
                email_taken = lazy_gettext('Email taken')
                flash(email_taken, 'error')
                return redirect(url_for('auth.login'))

            user = register_user(email, password, username)
            send_confirm_email(email)
            session['register_email'] = None
            session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, public=user.public,\
                                   email_subscribed=user.email_subscribed, email_verified=user.email_verified, contributor=user.contributor)
            conf_email_sent = lazy_gettext('Confirmation email sent')
            flash(conf_email_sent, 'success')
            return redirect(url_for('settings.index'))

        if user_and_password_is_valid(email, password):
            user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()

            session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, public=user.public,\
                                   email_subscribed=user.email_subscribed, email_verified=user.email_verified, contributor=user.contributor)

            newSettings = dict(user.settings)
            session['locale'] = newSettings['locale']
            session['theme'] = newSettings['theme']
            session['playnext'] = newSettings['playnext']

            session['navtabs']['navtab1'] = user.navtabs[0]
            session['navtabs']['navtab2'] = user.navtabs[1]
            session['navtabs']['navtab3'] = user.navtabs[2]

            session['navtabs_index']['navtab1'] = user.navtabs_index[0]
            session['navtabs_index']['navtab2'] = user.navtabs_index[1]
            session['navtabs_index']['navtab3'] = user.navtabs_index[2]

            if not user.email_verified:
                send_confirm_email(email)
                conf_email_resent = lazy_gettext('Email not verified, confirmation email resent')
                flash(conf_email_resent, 'error')

            return redirect(url_for('video.index'))

        else:
            email_pw_bad = lazy_gettext('Email and password combination is invalid')
            flash(email_pw_bad, 'error')


    return render_template('/auth/auth_index.html')

@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    email = confirm_token(token, 3600)
    if email == False:
        conf_bad = lazy_gettext('The confirmation link is invalid or has expired')
        flash(conf_bad, 'error')
        return redirect(url_for('video.index'))
    user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()

    if user.email_verified:
        session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, \
                               public=user.public, email_verified=user.email_verified, email_subscribed=user.email_subscribed)
        acct_conf = lazy_gettext('Account already confirmed. Please login')
        flash(acct_conf, 'success')
        return redirect(url_for('video.index'))
    else:
        now = datetime.datetime.now(timezone.utc)
        user.email_verified = True
        user.email_verified_date = now
        user.updated = now
        db_session.add(user)
        db_session.commit()
        if session.get('user') is not None:
            session['user']['email_verified'] = True
        txs_conf = lazy_gettext('Thank-you for confirming your account')
        flash(txs_conf, 'success')
    return redirect(url_for('video.index'))


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token, 3600)
    if email == False:
        reset_bad = lazy_gettext('The reset password link is invalid or has expired')
        flash(reset_bad, 'error')
        return redirect(url_for('video.index'))
    if request.method == 'GET':
        return render_template('auth/auth_reset_password.html', locale=util.get_locale(), token=token)
    elif request.method == 'POST':
        password = request.form['password']
        db_session.query(User).filter(User.email == email).update({"password": generate_password_hash(password),})
        db_session.commit()
        pw_updated = lazy_gettext('Password has been updated')
        flash(pw_updated, 'success')
        return redirect(url_for('video.index'))


@bp.route('/logout')
@login_required
def logout():
    now = datetime.datetime.now(timezone.utc)
    user = db_session.query(User).filter(User.email == session['user']['email']).one()
    user.updated = now
    user.settings = {
        "theme": session['theme'],
        "locale": session['locale'],
        "playnext": session['playnext']
    }

    user.navtabs =  [ session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3'] ]
    user.navtabs_index =  [ session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3'] ]
    db_session.commit()

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
            user = db_session.query(User).filter(User.id == user_id).first()
            db_session.delete(user)
            db_session.commit()
            flash(item_quoted + ' deleted', 'success')
            session['user'] = None
            return redirect(url_for('video.index'))
        else:
            flash(item_quoted + ' NOT deleted', 'error')
            return redirect(request.args.get('original_url', '/'))
    return render_template('widgets/widgets_confirm.html', message=message)