import boto3
import logging
from flask import url_for, render_template
from itsdangerous import URLSafeTimedSerializer
from mailjet_rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from .. import config

logger = logging.getLogger(__name__)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    return serializer.dumps(email, salt=config.SECURITY_PASSWORD_SALT)


def confirm_token(token, expiration):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    try:
        email = serializer.loads(token, salt=config.SECURITY_PASSWORD_SALT, max_age=expiration)
    except Exception:
        return False
    return email


def send_confirm_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    sender = config.SES_EMAIL_SOURCE_WELCOME
    subject = 'Welcome to altCensored.com! Confirm your Email for Full Access'
    html = render_template('auth/auth_activate.html', confirm_url=confirm_url)
    send_all_mass_email(email, sender, subject, html, service='aws')


def send_forgot_password_email(email, content):
    message = Mail(
        from_email='registration@altCensored.com',
        to_emails=email,
        subject='altCensored: Reset your password',
        html_content=content)
    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def send_sgrid_email(email, subject, content):
    message = Mail(
        from_email='admin@altCensored.com',
        to_emails=email,
        subject=subject,
        html_content=content)
    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def send_all_mass_email(email, sender, subject, html, service):
    if service == 'sgrid':
        message = Mail(from_email=sender, to_emails=email, subject=subject, html_content=html)
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        sg.send(message)

    if service == 'aws':
        ses = boto3.client(
            'ses',
            region_name=config.SES_REGION_NAME,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        ses.send_email(
            Source=sender,
            Destination={'ToAddresses': list((email,))},
            Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': html}}},
        )

    if service == 'mjet':
        mailjet = Client(auth=(config.MJ_API_KEY, config.MJ_API_SECRET), version='v3.1')
        data = {
            'Messages': [{
                "From": {"Email": sender, "Name": "altCensored"},
                "To": [{"Email": email}],
                "Subject": subject,
                "HTMLPart": html,
            }]
        }
        mailjet.send.create(data=data)
