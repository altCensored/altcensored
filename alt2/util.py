from flask import session, request
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer
from . import config

def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    return session['locale']


def get_theme():
    return session.get('theme', 'light')


def get_navtabs():
    if 'navtabs' in session:
        return session['navtabs']
    else:
        session['navtabs'] = config.SUPPORTED_NAVTABS
    return session['navtabs']


def send_welcome_email(email,content):
    message = Mail(
    from_email='registration@altCensored.com',
    to_emails=email,
    subject='Welcome to altCensored! Confirm your Email',
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
