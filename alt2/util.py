from flask import session, request
from . import config


def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    return session['locale']