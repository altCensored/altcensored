from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session, make_response, abort
from flask_login import login_user, logout_user, current_user
from flask_babelplus import gettext as _, lazy_gettext as _l
from urllib.parse import urlsplit
import requests
import secrets
import sqlalchemy as sa
from sqlalchemy import or_, func
from urllib.parse import urlencode
from alt2.database import db_session
from alt2.auth import bp
from alt2 import config
from alt2.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from alt2.models import User
from alt2.auth.email import send_password_reset_email, send_welcome_email
from alt2.util import create_user_altcen, login_user_altcen, logout_user_altcen, login_required, verify_turnstile_token

url_orig = config.RANDOM_VALUE

#  cflare testing, always fails
#
#cloudflare_site_key = "2x00000000000000000000AB"
#cloudflare_secret_key = "2x0000000000000000000000000000000AA"
cloudflare_site_key = config.CLOUDFLARE_SITE_KEY
cloudflare_secret_key = config.CLOUDFLARE_SECRET_KEY


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
            invalid_username_password = _('Invalid username or password')
            flash(invalid_username_password, 'error')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        login_user_altcen(user)
        if not user.email_verified:
            send_welcome_email(user)
            conf_email_sent = _l('Confirmation email sent')
            flash(conf_email_sent, 'success')
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('video.index')
        response = make_response(redirect(url_for('video.index')))
        response.set_cookie(url_orig, '1', httponly=True, samesite='Lax')  # Cookie expires in 1 hour
        return response
    return render_template('auth/login.html', title=_('Log In'), form=form, cloudflare_site_key=cloudflare_site_key)


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
        turnstile_token = request.form.get('cf-turnstile-response')
        verification_result = verify_turnstile_token(turnstile_token, cloudflare_secret_key)
        if verification_result.get('success'):
            create_user_altcen(user)
            send_welcome_email(user)
            conf_email_sent = _l('Confirmation email sent')
            flash(conf_email_sent, 'success')
            return redirect(url_for('auth.login'))
        else:
            cloudflare_failed = _('Cloudflare Turnstile Captcha Failed')
            flash(cloudflare_failed, 'error')
            return redirect(url_for('video.index'))

    return render_template('auth/register.html', title=_('Register'),
                           form=form,  cloudflare_site_key=cloudflare_site_key)


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
        password_reset_emailed = _('Check your email for password reset instructions')
        flash(password_reset_emailed, 'success')
        return redirect(url_for('video.index'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'), form=form, cloudflare_site_key=cloudflare_site_key)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('video.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('video.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db_session.commit()
        password_reset = _('Your password has been reset.')
        flash(password_reset, 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


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
        return redirect(url_for('auth.login'))
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
    return redirect(url_for('auth.login'))


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


@bp.route('/authorize/<provider>')
def oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('video.index'))

    provider_data = config.OAUTH2_PROVIDERS.get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session['oauth2_state'] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode({
        'client_id': provider_data['client_id'],
        'redirect_uri': url_for('auth.oauth2_callback', provider=provider,
                                _external=True),
        'response_type': 'code',
        'scope': ' '.join(provider_data['scopes']),
        'state': session['oauth2_state'],
    })

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data['authorize_url'] + '?' + qs)


@bp.route('/callback/<provider>')
def oauth2_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('video.index'))

    provider_data = config.OAUTH2_PROVIDERS.get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if 'error' in request.args:
        for k, v in request.args.items():
            if k.startswith('error'):
                flash(f'{k}: {v}')
        return redirect(url_for('video.index'))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args['state'] != session.get('oauth2_state'):
        abort(401)

    # make sure that the authorization code is present
    if 'code' not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response = requests.post(provider_data['token_url'], data={
        'client_id': provider_data['client_id'],
        'client_secret': provider_data['client_secret'],
        'code': request.args['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('auth.oauth2_callback', provider=provider,
                                _external=True),
    }, headers={'Accept': 'application/json'})
    if response.status_code != 200:
        abort(401)
    oauth2_token = response.json().get('access_token')
    if not oauth2_token:
        abort(401)

    # use the access token to get the user's email address
    response = requests.get(provider_data['userinfo']['url'], headers={
        'Authorization': 'Bearer ' + oauth2_token,
        'Accept': 'application/json',
    })
    if response.status_code != 200:
        abort(401)
    email = provider_data['userinfo']['email'](response.json())

    # find or create the user in the database
    user = db_session.scalar(sa.select(User).where(User.email == email))
    if user is None:
        user = User(email=email, username=email.split('@')[0])
#        db_session.add(user)
        create_user_altcen(user)
#        db_session.commit()

    # log the user in
    login_user(user)
    login_user_altcen(user)
    response = make_response(redirect(url_for('video.index')))
    response.set_cookie(url_orig, '1', httponly=True, samesite='Lax')  # Cookie expires in 1 hour
    return response