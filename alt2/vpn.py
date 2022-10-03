import os, io, csv
from threading import Thread
from flask import (Blueprint, session, render_template, flash, request, redirect, url_for, current_app, send_from_directory, \
                   send_file)
from .util import (login_required, email_verified_required, contributor_required, wg_api_call, \
                   generate_add_key_data_raw, add_key_to_conn, admin_login_required, string_boolean, update_conns )
from .models import Vpn_node, Vpn_conn
from . import config

bp = Blueprint('vpn', __name__, url_prefix='/vpn' )

@bp.route('/')
#@login_required
# remove '{% if session.user.xxx %}' in html for prod.
def index():
    node = request.args.get('node', None)
    conn = request.args.get('conn', None)
    submit = request.args.get('submit', None)
    tdata = None

    if session.get('user') is None:
        flash('Account required for free VPN','error')
        return redirect(url_for('auth.login'))

    if submit == 'new_conn' and not node:
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
        add_key_to_conn(data_raw, newkey, node, privkey, node_fqdn)

    conns = Vpn_conn.query.filter_by(altcen_user_id=(session['user']['id'])).all()

    if not session['user']['contributor'] and conns:
        nodes = None
    elif not session['user']['contributor']:
        nodes = Vpn_node.query.filter(Vpn_node.free.is_(True)).all()
    else:
        nodes = Vpn_node.query.all()

    return render_template('vpn/vpn_index.html', nodes=nodes, conns=conns, tdata=tdata)


@bp.route('/conn_action', methods=['POST'])
def conn_action():
    download = request.form['download']
    name = request.form['name']

    if download:
        filename = name+'.conf'
        mem_text_file = io.StringIO(download)
        # Creating the byteIO object from the StringIO Object
        mem = io.BytesIO()
        mem.write(mem_text_file.getvalue().encode())
        mem.seek(0)

        return send_file(
            mem,
            as_attachment=True,
            attachment_filename=filename,
            mimetype='text/csv')

    return redirect(url_for('vpn.index'))


@bp.route('/update')
@admin_login_required
def update():
    Thread(target=update_conns()).start()

    return redirect(url_for('vpn.index'))
