from flask import (Blueprint, session, render_template, flash, request, redirect, url_for)
from .util import (login_required, email_verified_required, contributor_required, wg_api_call,\
                   generate_add_key_data_raw, add_key_to_conn )
from .models import Vpn_node, Vpn_conn
from . import config

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
#@login_required
# remove '{% if session.user.xxx %}' in html for prod.
def index():
    node = request.args.get('node', None)
    submit = request.args.get('submit', None)
    tdata = None
    if session.get('user') is None:
        flash('Account required for FreeVPN','error')
        return redirect(url_for('auth.login'))

    if submit and not node:
        flash('Choose a node and try again','error')
    elif node:
        #
        # check if user already has max node connection to bail
        #

        conns_count = Vpn_conn.query. \
            filter_by(vpn_node_name=(node)). \
            filter_by(altcen_user_id=(session['user']['id'])). \
            count()

        if session['user']['contributor'] and conns_count > 1:
            flash('Maximum 2 Connections per Node', 'error')
            conns = Vpn_conn.query.filter_by(altcen_user_id=(session['user']['id'])).all()
            nodes = Vpn_node.query.all()
            return render_template('vpn/vpn_index.html', nodes=nodes, conns=conns, tdata=tdata)

        #
        # create new profile on selected node w/fqdn and free flag
        #

        node_obj = Vpn_node.query.filter(Vpn_node.name == node).one()
        node_fqdn = node_obj.fqdn
        if node_obj.free:
            p_bwLimit = config.VPN_FREE_BWLIMIT
        else:
            p_bwLimit = config.VPN_DEFAULT_BWLIMIT

        #
        # create json, set vars, create key, and write to db
        #

        data_raw, privkey = generate_add_key_data_raw(p_bwLimit)
        method = 'POST'
        api_request = '/manager/key'
        newkey = wg_api_call(node_fqdn, api_request, method, data_raw)
        add_key_to_conn(data_raw, newkey, node, privkey)

    conns = Vpn_conn.query.filter_by(altcen_user_id=(session['user']['id'])).all()

    if not session['user']['contributor'] and conns:
        nodes = None
    elif not session['user']['contributor']:
        nodes = Vpn_node.query.filter(Vpn_node.free.is_(True)).all()
    else:
        nodes = Vpn_node.query.all()

    return render_template('vpn/vpn_index.html', nodes=nodes, conns=conns, tdata=tdata)
