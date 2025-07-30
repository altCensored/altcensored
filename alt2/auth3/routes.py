from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from flask_babelplus import gettext as _, lazy_gettext as _l
from urllib.parse import urlsplit
import sqlalchemy as sa
from sqlalchemy import or_, func
from alt2.database import db_session
from alt2.auth3 import bp
from alt2.auth3.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from alt2.models import User
from alt2.auth3.email import send_password_reset_email, send_welcome_email
from alt2.util import create_user_altcen, login_user_altcen, logout_user_altcen, login_required


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('video.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db_session.scalar(
            sa.select(User)
            .where(or_(User.username == form.username.data,User.email == form.username.data )))
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth3.login'))
        login_user(user, remember=form.remember_me.data)
        login_user_altcen(user)
        if not user.email_verified:
            send_welcome_email(user)
            conf_email_sent = _l('Confirmation email sent')
            flash(conf_email_sent, 'success')
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('video.index')
        return redirect(next_page)
    return render_template('auth3/login.html', title=_('Sign In'), form=form)


@bp.route('/logout')
def logout():
    logout_user()
    logout_user_altcen()
    return redirect(url_for('video.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('videos.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        create_user_altcen(user)
#        send_welcome_email(user)
#        conf_email_sent = _l('Confirmation email sent')
#        flash(conf_email_sent, 'success')
        return redirect(url_for('auth3.login'))
    return render_template('auth3/register.html', title=_('Register'),
                           form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('video.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db_session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash(
            _('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth3.login'))
    return render_template('auth3/reset_password_request.html',
                           title=_('Reset Password'), form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db_session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth3.login'))
    return render_template('auth3/reset_password.html', form=form)


@bp.route('/confirm_email/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    user = User.verify_reset_password_token(token)
    if not user:
        conf_bad = _l('The confirmation link is invalid or has expired')
        flash(conf_bad, 'error')
        return redirect(url_for('video.index'))

    if user.email_verified:
        session['user'] = dict(id=user.id, email=user.email, username=user.username, description=user.description, \
                               public=user.public, email_verified=user.email_verified, email_subscribed=user.email_subscribed)
        acct_conf = _l('Account already confirmed. Please login')
        flash(acct_conf, 'success')
        return redirect(url_for('video.index'))
    else:
        now = datetime.now(timezone.utc)
        user.email_verified = True
        user.email_verified_date = now
        user.updated = now
        db_session.add(user)
        db_session.commit()
        if session.get('user') is not None:
            session['user']['email_verified'] = True
        txs_conf = _l('Thank-you for confirming your account')
        flash(txs_conf, 'success')
    return redirect(url_for('video.index'))


@bp.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    user_id = session['user']['id']
    user_email = session['user']['email']
    l_msg = _l('Delete User')+' '
    item_quoted = f'"{user_email}"'
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
            return redirect(request.args.get(url_orig, '/'))
    return render_template('widgets/widgets_confirm.html', message=message)