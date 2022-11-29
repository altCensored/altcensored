import functools, os, string, random, subprocess, requests, datetime, qrcode, base64
import boto3

from flask import (
    session, request, redirect, render_template, url_for, current_app, flash
)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer
from better_profanity import profanity
from sqlalchemy import func
from captcha.image import ImageCaptcha
from email_validator import validate_email, EmailNotValidError
from mailjet_rest import Client
from flask_babelplus import lazy_gettext
from datetime import timezone
from io import BytesIO
from .database import db_session
from .models import Translation, Playlist, Mv_Channel, Mv_Video, User, \
    Email_list, Channels, Channels_part, Vpn_node, Vpn_conn, Entity, Source
from . import config


def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')
    return session['locale']


def get_theme():
    return session.get('theme', 'light')


def get_playnext():
    if 'playnext' in session:
        return session['playnext']
    else:
        session['playnext'] = False
    return session['playnext']


def get_looplist():
    if 'looplist' in session:
        return session['looplist']
    else:
        session['looplist'] = True
    return session['looplist']


def get_navtabs():
    if 'navtabs' in session:
        return session['navtabs']
    else:
        row = db_session.query(Translation).with_entities(Translation.varname,
                                                          getattr(Translation, session['locale'])).all()
        rowtuple = tuple(row)
        session['navtabs'] = dict(rowtuple)
    return session['navtabs']


def get_navtabs_index():
    if 'navtabs_index' in session:
        return session['navtabs_index']
    else:
        row = db_session.query(Translation).with_entities(Translation.varname, Translation.en).all()
        rowtuple = tuple(row)
        session['navtabs_index'] = dict(rowtuple)
    return session['navtabs_index']


def get_navtabs_perm():
    session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    row = db_session.query(Translation).with_entities(Translation.varname,
                                                      getattr(Translation, session['locale'])).all()
    rowtuple = tuple(row)
    navtabs_perm = dict(rowtuple)
    return navtabs_perm


def get_videocount():
    if 'videocount' in session:
        return session['videocount']
    else:
        session['videocount'] = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    return session['videocount']


def get_channelcount():
    if 'channelcount' in session:
        return session['channelcount']
    else:
        session['channelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    return session['channelcount']


def get_delchannelcount():
    if 'delchannelcount' in session:
        return session['delchannelcount']
    else:
        session['delchannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(
            Mv_Channel.ytc_deleted).scalar()
    return session['delchannelcount']


def set_session() -> object:
    """
    :rtype: object
    """
    if 'locale' in session:
        pass
    else:
        #        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')

    if 'theme' in session:
        pass
    else:
        session['theme'] = 'light'

    if 'playnext' in session:
        pass
    else:
        session['playnext'] = False

    if 'looplist' in session:
        pass
    else:
        session['looplist'] = True

    if 'navtabs' in session:
        pass
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')
        row = db_session.query(Translation).with_entities(Translation.varname,
                                                          getattr(Translation, session['locale'])).all()
        rowtuple = tuple(row)
        session['navtabs'] = dict(rowtuple)

    if 'navtabs_index' in session:
        pass
    else:
        row = db_session.query(Translation).with_entities(Translation.varname, Translation.en).all()
        rowtuple = tuple(row)
        session['navtabs_index'] = dict(rowtuple)

    if 'navtabs_perm' in session:
        pass
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')
        row = db_session.query(Translation).with_entities(Translation.varname,
                                                          getattr(Translation, session['locale'])).all()
        rowtuple = tuple(row)
        session['navtabs_perm'] = dict(rowtuple)

    if 'videocount' in session:
        pass
    else:
        session['videocount'] = db_session.query(func.count(Mv_Video.extractor_data)).scalar()

    if 'usercount' in session:
        pass
    else:
        session['usercount'] = db_session.query(func.count(User.id).filter(User.public)).scalar()

    if 'playlistcount' in session:
        pass
    else:
        session['playlistcount'] = db_session.query(
            func.count(Playlist.id).filter(Playlist.public).filter(Playlist.featured_video.isnot(None))).scalar()

    if 'channelcount' in session:
        pass
    else:
        session['channelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()

    if 'delchannelcount' in session:
        pass
    else:
        session['delchannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(
            Mv_Channel.ytc_deleted).scalar()


def send_confirm_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    html = render_template('auth/auth_activate.html', confirm_url=confirm_url)
    send_welcome_email(email, html)


def send_welcome_email(email, content):
    message = Mail(
        from_email='registration@altCensored.com',
        to_emails=email,
        subject='Welcome to altCensored.com! Confirm your Email for Full Access',
        html_content=content)

    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def send_forgot_password_email(email, content):
    message = Mail(
        from_email='registration@altCensored.com',
        to_emails=email,
        subject='altCensored: Reset your password',
        html_content=content)

    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    return serializer.dumps(email, salt=config.SECURITY_PASSWORD_SALT)


def confirm_token(token, expiration):
    serializer = URLSafeTimedSerializer(config.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=config.SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
    except:
        return False
    return email


def str_to_bool(s) -> object:
    """

    :rtype: 
    """
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError


def contains_profanity(dirty_text):
    if profanity.contains_profanity(dirty_text):
        return True
    else:
        return False


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view


def admin_login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session['user']['username'] != 'admin':
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view


def email_verified_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session['user']['email_verified']:
            msg = lazy_gettext('Email verification is required for VPN')
            flash(msg, 'error')
            return redirect(url_for('settings.index'))
        return view(**kwargs)
    return wrapped_view


def contributor_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session['user']['contributor']:
#            msg = lazy_gettext('Contributor status is required for premium VPN')
#            flash(msg, 'error')
            return redirect(url_for('settings.index'))
        return view(**kwargs)
    return wrapped_view


def email_exists(email):
    if session.get('email') is not None:
        if email == session['user']['email']:
            return False
    if db_session.query(User.email).filter(func.lower(User.email) == func.lower(email)).scalar() is not None:
        return True


def email_list_exists(email):
    if db_session.query(Email_list.email).filter(
            func.lower(Email_list.email) == func.lower(email)).scalar() is not None:
        return True


def validate_user_email(email):
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return e


def username_exists(username):
    if username == session['user']['username']:
        return False
    if db_session.query(User.username).filter(func.lower(User.username) == func.lower(username)).scalar() is not None:
        return True


def generate_random(size=4, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for _ in range(size))


def response_success(sub_reset):
    response = sub_reset['response']
    if 'success' in response:
        return True


def create_captcha(myrandom, mycaptcha):
    image = ImageCaptcha()
    data = image.generate(str(myrandom))
    image.write(str(myrandom), os.path.join(current_app.static_folder, mycaptcha))


def title_exists(ftitle):
    user_id = session['user']['id']
    if db_session.query(Playlist.title).filter((Playlist.title) == (ftitle)).filter(
            (Playlist.user_id) == (user_id)).scalar() is not None:
        return True


def channel_partial_add(channel_id):
    if db_session.query(Channels_part.ytc_id).filter((Channels_part.ytc_id) == (channel_id)).scalar() is not None:
        return True
    else:
        channel_part = Channels_part(ytc_id=channel_id)
        db_session.add(channel_part)
        db_session.commit()


def channel_full_add(channel_url):
    if db_session.query(Channels.url).filter((Channels.url) == (channel_url)).scalar() is not None:
        return True
    else:
        channel_full = Channels(url=channel_url)
        db_session.add(channel_full)
        db_session.commit()


def channel_partial_remove(channel_id):
    if db_session.query(Channels_part.ytc_id).filter(Channels_part.ytc_id == channel_id).scalar() is not None:
        channel_part = Channels_part.query.filter(Channels_part.ytc_id == channel_id).first()
        db_session.delete(channel_part)
        db_session.commit()
        return False
    else:
        return True


def channel_full_remove(channel_url):
    if db_session.query(Channels.url).filter(Channels.url == channel_url).scalar() is not None:
        channel_full = Channels.query.filter(Channels.url == channel_url).first()
        db_session.delete(channel_full)
        db_session.commit()
        return False
    else:
        return True


def ssh_command(sys_name, commands):
    ssh_host = 'root@' + sys_name
    for command in commands:
        ssh = subprocess.Popen(["ssh", "%s" % ssh_host, command],
                               shell=False,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        result = ssh.stdout.readlines()
        if not result:
            error = ssh.stderr.readlines()
            flash(error, 'error')
        else:
            flash(result, 'success')


def video_toggle_allow(video_id, bool_allow=None, bool_deleted=None):
    try:
        video = Entity.query.filter(Entity.extractor_data == video_id).first()
        if bool_allow is not None:
            video.allow = bool_allow
        if bool_deleted is not None:
            video.yt_deleted = bool_deleted
        db_session.commit()
        return True
    except:
        return False


def channel_update(channel_id, delta=None, archive_type=None, deleted=None, viewcount=None, subscribercount=None, deleteddate=None):
    try:
        channel = Source.query.filter(Source.ytc_id == channel_id).first()

        if delta:
            channel.delta = delta

        if archive_type:
            if archive_type == 'none':
                channel.ytc_archive = False
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = False
            elif archive_type == 'partial':
                channel.ytc_archive = False
                channel.ytc_partarchive = True
                channel.ytc_latestarchive = False
            elif archive_type == 'full':
                channel.ytc_archive = True
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = False
            elif archive_type == 'latest':
                channel.ytc_archive = False
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = True

        if deleted is True or deleted is False:
            channel.ytc_deleted = deleted
        if viewcount:
            channel.ytc_viewcount = viewcount
        if subscribercount:
            channel.ytc_subscribercount = subscribercount
        if deleteddate:
            channel.ytc_deleteddate = deleteddate
        db_session.commit()
        return True
    except:
        return False


def send_sgrid_email(email, subject, content):
    message = Mail(
        from_email='admin@altCensored.com',
        to_emails=email,
        subject=subject,
        html_content=content)

    sg = SendGridAPIClient(config.SENDGRID_API_KEY)
    sg.send(message)


def send_all_mass_email(email, subject, html, service):
    if service == 'sgrid':
        message = Mail(
            from_email='admin@altCensored.com',
            to_emails=email,
            subject=subject,
            html_content=html)

        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        sg.send(message)

    if service == 'aws':
        email = list((email,))
        ses = boto3.client(
            'ses',
            region_name=config.SES_REGION_NAME,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
        )
        sender = config.SES_EMAIL_SOURCE
        ses.send_email(
            Source=sender,
            Destination={'ToAddresses': email},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html}
                }
            },
        )

    if service == 'mjet':
        mailjet = Client(auth=(config.MJ_API_KEY, config.MJ_API_SECRET), version='v3.1')
        sender = "newsletter@altcensored.com"
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": sender,
                        "Name": "altCensored"
                    },
                    "To": [
                        {
                            "Email": email,
                        }
                    ],
                    "Subject": subject,
                    "HTMLPart": html
                }
            ]
        }
        result = mailjet.send.create(data=data)


def wg_api_call(node_fqdn, api_request, method='GET', data_raw=None):
    url = 'https://' + node_fqdn + ':' + config.VPN_API_PORT + api_request
    headers = {'Authorization':config.VPN_API_AUTH}
    r = requests.request(method, url, headers=headers, json=data_raw)
    data = r.json()
    return data


def generate_add_key_data_raw(p_bwLimit=config.VPN_FREE_BWLIMIT, *args, **kwargs):
    p_subExpiry = kwargs.get('b', config.VPN_DEFAULT_SUBEXPIRY)
    p_ipIndex = kwargs.get('c', config.VPN_DEFAULT_IPINDEX)

    privkey = subprocess.check_output("wg genkey", shell=True).decode("utf-8").strip()
    pubkey = subprocess.check_output(f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
    sharedkey = subprocess.check_output("wg genpsk", shell=True).decode("utf-8").strip()

    data_raw = {
        "publicKey": pubkey,
        "presharedKey": sharedkey,
        "bwLimit": p_bwLimit,
        "subExpiry": p_subExpiry,
        "ipIndex": p_ipIndex
    }
    return data_raw, privkey


def add_key_to_conn(data_raw, newkey, node, privkey, node_fqdn):
    l1='[Interface]'
    l2='PrivateKey = '+privkey
    l3='Address = '+newkey['ipv4Address']
    l4='Address = '+newkey['ipv6Address']
    l5='DNS = '+newkey['dns']
    l6=None
    l7='[Peer]'
    l8='PublicKey = '+newkey['publicKey']
    l9='PresharedKey = '+data_raw['presharedKey']
    l10='AllowedIPs = '+newkey['allowedIPs']
    l11='Endpoint = '+node_fqdn+':'+config.VPN_PORT

    config_file=l1+chr(10)+l2+chr(10)+l3+chr(10)+l4+chr(10)+l5+chr(10)+chr(10)+l7+chr(10)+l8+chr(10)+l9+chr(10)+l10+chr(10)+l11+chr(10)
    image = qrcode.make(config_file)
    bytesbuf = BytesIO()
    image.save(bytesbuf, format='PNG')
    bytes_out = bytesbuf.getvalue()
    encoded = base64.b64encode(bytes_out)
    encoded_ascii = encoded.decode('ascii')

    now = datetime.datetime.now(timezone.utc)
    vpn_conn = Vpn_conn(\
        publickey=data_raw['publicKey'], vpn_node_name=node, altcen_user_id=session['user']['id'], privatekey=privkey, \
        sharedkey=data_raw['presharedKey'], key_id=newkey['keyID'], bw_limit=data_raw['bwLimit'], bw_used=0, \
        sub_expiry=data_raw['subExpiry'], expired=False, enabled=True, allowedips=newkey['allowedIPs'], dns=newkey['dns'], \
        ipaddress=newkey['ipAddress'], ipv4address=newkey['ipv4Address'], ipv6address=newkey['ipv6Address'], created=now, \
        vpn_node_publickey=newkey['publicKey'], vpn_node_fqdn=node_fqdn, config_file=config_file, config_qrcode=encoded_ascii \
        )
    db_session.add(vpn_conn)
    db_session.commit()


def string_boolean(text):
    if text.lower() in ['true', '1', 't', 'y', 'yes']:
        return True
    else:
        return False


def update_conns():
    nodes = Vpn_node.query.filter(Vpn_node.free).all()
    for node in nodes:
        node_fqdn = node.fqdn
        #
        # update keys for 'Enabled'
        #
        api_request = '/manager/key'
        keys_upd = wg_api_call(node_fqdn, api_request)
        keys = keys_upd['Keys']
        for key in keys:
            conn = Vpn_conn.query. \
                    filter_by(vpn_node_name=node.name). \
                    filter_by(key_id=key['KeyID']). \
                    scalar()
            if conn is not None:
                conn.enabled = string_boolean(key['Enabled'])
        #
        # update subs for 'BandwidthUsed'
        #
        api_request = '/manager/subscription/all'
        subs_upd = wg_api_call(node_fqdn, api_request)
        subs = subs_upd['subscriptions']
        for sub in subs:
            conn = Vpn_conn.query. \
                    filter_by(vpn_node_name=node.name). \
                    filter_by(key_id=sub['KeyID']). \
                    scalar()
            if conn is not None:
                conn.bw_used = sub['BandwidthUsed']

    db_session.commit()


def reset_conns():
    conns = Vpn_conn.query. \
        filter(Vpn_conn.bw_used != 0). \
        all()
    for conn in conns:
        #
        # reset bwidth used
        #
        node_fqdn = conn.vpn_node_fqdn
        api_request = '/manager/subscription/edit'
        method = 'POST'
        data_raw = {
            "keyID": str(conn.key_id),
            "subExpiry": "2032-Oct-21 12:49:05 PM",
            "bwReset": True
        }
        reset_bw = wg_api_call(node_fqdn, api_request, method, data_raw)
        if response_success(reset_bw):
            conn.bw_used = 0
        #
        # enable
        #
        api_request = '/manager/key/enable'
        method = 'POST'
        data_raw = {
            "keyID": str(conn.key_id),
        }
        enable_key = wg_api_call(node_fqdn, api_request, method, data_raw)
        if response_success(enable_key):
            conn.enabled = True
    db_session.commit()
