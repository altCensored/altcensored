from flask import (Blueprint, session, render_template, flash)

from .util import email_verified_required, wg_keys_exist, generate_wireguard_keys
from . import util

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
@email_verified_required
def index():
#    if wg_keys_exist():
#        flash('key exist')
#    else:
#        flash('keys do not exist')

    return render_template('vpn/vpn_index.html')


