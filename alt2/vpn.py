from flask import (Blueprint, render_template)

from .util import set_session, email_verified_required
from . import util

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
@email_verified_required
def index():
    set_session()
    return render_template('vpn/vpn_index.html')


