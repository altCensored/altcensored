from flask import render_template, current_app
from flask_babelplus import gettext as _
from alt2.email import send_email


def send_welcome_email(user):
    token = user.get_reset_password_token()
    send_email(_('Welcome to altCensored.com! Confirm your Email for Full Access'),
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/welcome.txt',
                                         user=user, token=token),
               html_body=render_template('email/welcome.html',
                                         user=user, token=token))


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(_('altCensored.com Reset Your Password'),
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))
