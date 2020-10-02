from flask import (
    session, request, redirect, url_for, current_app
    )
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer
from better_profanity import profanity
from sqlalchemy import func, text, desc
from captcha.image import ImageCaptcha
from .database import db_session
from .models import Translation, Playlist
from . import config
import functools, os, string, random


def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    return session['locale']

def get_theme():
    return session.get('theme', 'light')

def get_playnext():
    if 'playnext' in session:
        return session['playnext']
    else:
        session['playnext'] = False
    return session['playnext']

def get_looplist():
    if 'looplist' in session:
        return session['looplist']
    else:
        session['looplist'] = True
    return session['looplist']

def get_navtabs():
    if 'navtabs' in session:
        return session['navtabs']
    else:
        row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
        rowtuple = tuple(row)
        session['navtabs'] = dict(rowtuple)
    return session['navtabs']


def get_navtabs_index():
    if 'navtabs_index' in session:
        return session['navtabs_index']
    else:
        row = db_session.query(Translation).with_entities(Translation.varname,Translation.en).all()
        rowtuple = tuple(row)
        session['navtabs_index'] = dict(rowtuple)
    return session['navtabs_index']


def get_navtabs_perm():
    session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
    rowtuple = tuple(row)
    navtabs_perm = dict(rowtuple)
    return navtabs_perm


def send_welcome_email(email,content):
    message = Mail(
    from_email='registration@altCensored.com',
    to_emails=email,
    subject='Welcome to altCensored.com! Confirm your Email for Full Access',
    html_content=content)

    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def send_forgot_password_email(email,content):
    message = Mail(
        from_email='registration@altCensored.com',
        to_emails=email,
        subject='altCensored: Reset your password',
        html_content=content)

    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    return serializer.dumps(email, salt=config.SECURITY_PASSWORD_SALT)


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=config.SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
    except:
        return False
    return email


def str_to_bool(s):
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError


def contains_profanity(dirty_text):
    if profanity.contains_profanity(dirty_text):
        return True
    else:
        return False


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view


def username_exists(username):
    if username == session['user']['username']:
        return False
    if db_session.query(User.username).filter(func.lower(User.username) == func.lower(username)).scalar() is not None:
        return True


def generate_random(size=4, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for _ in range(size))


def create_captcha(myrandom, mycaptcha):
    image = ImageCaptcha()
    data = image.generate(str(myrandom))
    image.write(str(myrandom), os.path.join(current_app.static_folder, mycaptcha))


def title_exists(ftitle):
    user_id = session['user']['id']
    if db_session.query(Playlist.title).filter((Playlist.title) == (ftitle)).filter((Playlist.user_id) == (user_id)).scalar() is not None:
        return True