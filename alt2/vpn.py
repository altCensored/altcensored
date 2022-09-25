from flask import (Blueprint, session, render_template, flash)

from .util import email_verified_required, get_wg_keys, contributor_required
#from . import config

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
@email_verified_required
@contributor_required
def index():
#    flash(session)
    my_wg_keys = get_wg_keys()
    pubkey = my_wg_keys[0]
    sharedkey = my_wg_keys[1]
#    tdata = sharedkey
    tdata = pubkey
    return render_template('vpn/vpn_index.html', tdata=tdata)
