from flask_wtf import FlaskForm
from flask_babelplus import gettext as _, lazy_gettext as _l
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from alt2.database import db_session
from alt2.models import User
import sqlalchemy as sa


class LoginForm(FlaskForm):
#    username = StringField(_l('Username'), validators=[DataRequired()], render_kw={'placeholder': 'Username / Email'})
    username = StringField(_l('Username'), validators=[DataRequired()], render_kw={'placeholder': _l('Username')})
#    password = PasswordField(_l('Password'), validators=[DataRequired()], render_kw={'placeholder': 'Password'})
    password = PasswordField(_l('Password'), validators=[DataRequired()], render_kw={'placeholder': _l('Password')})
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()], render_kw={'placeholder': 'Username'})
    email = StringField(_l('Email'), validators=[DataRequired(), Email()], render_kw={'placeholder': 'Email'})
    password = PasswordField(_l('Password'), validators=[DataRequired()], render_kw={'placeholder': _l('Password')})
    password2 = PasswordField(
        _l('Password'), validators=[DataRequired(),
                                           EqualTo('password')], render_kw={'placeholder': _l('Password')})
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = db_session.scalar(sa.select(User).where(
            User.username == username.data))
        if user is not None:
            raise ValidationError(_('Please use a different username.'))

    def validate_email(self, email):
        user = db_session.scalar(sa.select(User).where(
            User.email == email.data))
        if user is not None:
            raise ValidationError(_('Please use a different email address.'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(),
                                           EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))
