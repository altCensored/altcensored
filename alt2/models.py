from altcen_models.db import (
    Base, MaterializedView,
    Entity, Sources_to_Videos, Video, Source,
    Category, Language, Translation, Counter,
    User, Playlist, EmailList,
    VpnNode, VpnConn, Crypto,
    MvVideo, MvChannel, MvCategory, MvPlaylist, MvAltcenUser,
)
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from .database import db_session
from time import time

# Backward-compat aliases for all blueprint imports
Email_list = EmailList
Mv_Video = MvVideo
Mv_Channel = MvChannel
Mv_Category = MvCategory
Mv_Playlist = MvPlaylist
Mv_Altcen_user = MvAltcenUser


def _set_password(self, password):
    self.password = generate_password_hash(password)


def _check_password(self, password):
    if not self.password:
        return False
    return check_password_hash(self.password, password)


def _get_reset_password_token(self, expires_in=3600):
    return jwt.encode(
        {'reset_password': self.id, 'type': 'reset_password', 'exp': time() + expires_in},
        current_app.config['SECRET_KEY'], algorithm='HS256')


def _verify_reset_password_token(token):
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        if payload.get('type') != 'reset_password':
            return None
        user_id = payload['reset_password']
    except Exception:
        return None
    return db_session.get(User, user_id)


User.set_password = _set_password
User.check_password = _check_password
User.get_reset_password_token = _get_reset_password_token
User.verify_reset_password_token = staticmethod(_verify_reset_password_token)
