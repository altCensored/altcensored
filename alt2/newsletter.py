from flask import (Blueprint, render_template)

from .util import set_session

bp = Blueprint('newsletter', __name__, url_prefix='/newsletter' )

@bp.route('/')
def index():
    set_session()
    return render_template('newsletter/newsletter_index.html')


