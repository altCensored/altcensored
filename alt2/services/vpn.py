import base64
import logging
import qrcode
import requests
import subprocess
from datetime import datetime, timezone
from io import BytesIO

from flask import session

from ..database import db_session
from ..models import Vpn_conn, Vpn_node
from .. import config

logger = logging.getLogger(__name__)


def string_boolean(text):
    return text.lower() in ['true', '1', 't', 'y', 'yes']


def response_success(sub_reset):
    return 'success' in sub_reset['response']


def wg_api_call(node_fqdn, api_request, method='GET', data_raw=None):
    url = 'https://' + node_fqdn + ':' + config.VPN_API_PORT + api_request
    headers = {'Authorization': config.VPN_API_AUTH}
    r = requests.request(method, url, headers=headers, json=data_raw, timeout=5)
    return r.json()


def generate_add_key_data_raw(p_bwLimit=config.VPN_FREE_BWLIMIT, *args, **kwargs):
    p_subExpiry = kwargs.get('b', config.VPN_DEFAULT_SUBEXPIRY)
    p_ipIndex = kwargs.get('c', config.VPN_DEFAULT_IPINDEX)

    privkey = subprocess.check_output("wg genkey", shell=True, timeout=30).decode("utf-8").strip()
    pubkey = subprocess.check_output(
        f"echo '{privkey}' | wg pubkey", shell=True, timeout=30
    ).decode("utf-8").strip()
    sharedkey = subprocess.check_output("wg genpsk", shell=True, timeout=30).decode("utf-8").strip()

    data_raw = {
        "publicKey": pubkey,
        "presharedKey": sharedkey,
        "bwLimit": p_bwLimit,
        "subExpiry": p_subExpiry,
        "ipIndex": p_ipIndex,
    }
    return data_raw, privkey


def add_key_to_conn(data_raw, newkey, node, privkey, node_fqdn):
    config_file = (
        '[Interface]' + chr(10) +
        'PrivateKey = ' + privkey + chr(10) +
        'Address = ' + newkey['ipv4Address'] + chr(10) +
        'Address = ' + newkey['ipv6Address'] + chr(10) +
        'DNS = ' + newkey['dns'] + chr(10) + chr(10) +
        '[Peer]' + chr(10) +
        'PublicKey = ' + newkey['publicKey'] + chr(10) +
        'PresharedKey = ' + data_raw['presharedKey'] + chr(10) +
        'AllowedIPs = ' + newkey['allowedIPs'] + chr(10) +
        'Endpoint = ' + node_fqdn + ':' + config.VPN_PORT + chr(10)
    )
    image = qrcode.make(config_file)
    bytesbuf = BytesIO()
    image.save(bytesbuf, format='PNG')
    encoded_ascii = base64.b64encode(bytesbuf.getvalue()).decode('ascii')

    vpn_conn = Vpn_conn(
        publickey=data_raw['publicKey'],
        vpn_node_name=node,
        altcen_user_id=session['user']['id'],
        privatekey=privkey,
        sharedkey=data_raw['presharedKey'],
        key_id=newkey['keyID'],
        bw_limit=data_raw['bwLimit'],
        bw_used=0,
        sub_expiry=data_raw['subExpiry'],
        expired=False,
        enabled=True,
        allowedips=newkey['allowedIPs'],
        dns=newkey['dns'],
        ipaddress=newkey['ipAddress'],
        ipv4address=newkey['ipv4Address'],
        ipv6address=newkey['ipv6Address'],
        created=datetime.now(timezone.utc),
        vpn_node_publickey=newkey['publicKey'],
        vpn_node_fqdn=node_fqdn,
        config_file=config_file,
        config_qrcode=encoded_ascii,
    )
    db_session.add(vpn_conn)
    db_session.commit()


def update_conns():
    nodes = Vpn_node.query.filter(Vpn_node.free).all()
    for node in nodes:
        node_fqdn = node.fqdn

        keys_upd = wg_api_call(node_fqdn, '/manager/key')
        for key in keys_upd['Keys']:
            conn = Vpn_conn.query.filter_by(vpn_node_name=node.name).filter_by(key_id=key['KeyID']).scalar()
            if conn is not None:
                conn.enabled = string_boolean(key['Enabled'])

        subs_upd = wg_api_call(node_fqdn, '/manager/subscription/all')
        for sub in subs_upd['subscriptions']:
            conn = Vpn_conn.query.filter_by(vpn_node_name=node.name).filter_by(key_id=sub['KeyID']).scalar()
            if conn is not None:
                conn.bw_used = sub['BandwidthUsed']

    db_session.commit()


def reset_conns():
    conns = Vpn_conn.query.filter(Vpn_conn.bw_used != 0).all()
    for conn in conns:
        node_fqdn = conn.vpn_node_fqdn

        reset_bw = wg_api_call(
            node_fqdn, '/manager/subscription/edit', 'POST',
            {"keyID": str(conn.key_id), "subExpiry": "2032-Oct-21 12:49:05 PM", "bwReset": True},
        )
        if response_success(reset_bw):
            conn.bw_used = 0

        enable_key = wg_api_call(
            node_fqdn, '/manager/key/enable', 'POST',
            {"keyID": str(conn.key_id)},
        )
        if response_success(enable_key):
            conn.enabled = True

    db_session.commit()
