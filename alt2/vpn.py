from flask import (Blueprint, render_template, flash)

from .util import email_verified_required, get_wg_publickey, contributor_required
#from . import config

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
@email_verified_required
@contributor_required
def index():
    my_wg_publickey = get_wg_publickey()
    tdata = my_wg_publickey

    return render_template('vpn/vpn_index.html', tdata=tdata)


