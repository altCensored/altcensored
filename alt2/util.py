import functools, os, string, random, subprocess, requests, datetime, qrcode, base64
import boto3

from better_profanity import profanity
from captcha.image import ImageCaptcha
from datetime import timezone
from email_validator import validate_email, EmailNotValidError
from flask import (
    session, request, redirect, render_template, url_for, current_app, flash
)
from flask_babelplus import lazy_gettext
from http.client import HTTPSConnection
from io import BytesIO
from internetarchive import get_item
from itsdangerous import URLSafeTimedSerializer
from mailjet_rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sqlalchemy import func, nullslast
from urllib.parse import urlparse

from sqlalchemy.orm.attributes import flag_modified

from .database import db_session
from .models import Translation, Playlist, Mv_Channel, Mv_Video, User, \
    Email_list, Channels, Channels_part, Vpn_node, Vpn_conn, Entity, Source, Counter
from . import config
from .cache import cache

video_url = None

def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')
    return session['locale']


def get_theme():
    if 'theme' in session:
        return session['theme']
    else:
        session['theme'] = config.DEFAULT_THEME
    return session['theme']

def get_playnext():
    if 'playnext' in session:
        return session['playnext']
    else:
        session['playnext'] = config.DEFAULT_PLAYNEXT
    return session['playnext']


def get_looplist():
    if 'looplist' in session:
        return session['looplist']
    else:
        session['looplist'] = config.DEFAULT_LOOPLIST
    return session['looplist']


def get_autoplay():
    if 'autoplay' in session:
        return session['autoplay']
    else:
        session['autoplay'] = config.DEFAULT_AUTOPLAY
    return session['autoplay']


def get_navtabs():
    if 'navtabs' in session:
        return session['navtabs']
    else:
        row = navtabs_cache(session['locale'])
#        row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
        rowtuple = tuple(row)
        session['navtabs'] = dict(rowtuple)
    return session['navtabs']


def get_navtabs_index():
    if 'navtabs_index' in session:
        return session['navtabs_index']
    else:
        row = navtabs_index_cache()
#        row = db_session.query(Translation).with_entities(Translation.varname, Translation.en).all()
        rowtuple = tuple(row)
        session['navtabs_index'] = dict(rowtuple)
    return session['navtabs_index']

#
# not being used
#
#def get_navtabs_perm():
#    session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
#    row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
#    rowtuple = tuple(row)
#    navtabs_perm = dict(rowtuple)
#    return navtabs_perm


def get_videocount():
    if 'videocount' in session:
        return session['videocount']
    else:
#        session['videocount'] = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
        session['videocount'] = videocount_cache()
    return session['videocount']


def get_channelcount():
    if 'channelcount' in session:
        return session['channelcount']
    else:
#        session['channelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
        session['channelcount'] = channelcount_cache()
    return session['channelcount']


def get_delchannelcount():
    if 'delchannelcount' in session:
        return session['delchannelcount']
    else:
#        session['delchannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
        session['delchannelcount'] = delchannelcount_cache()
    return session['delchannelcount']


def get_archivechannelcount():
    if 'archivechannelcount' in session:
        return session['archivechannelcount']
    else:
#        session['archivechannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
        session['archivechannelcount'] = archivechannelcount_cache()
    return session['archivechannelcount']


def get_playlistcount():
    if 'playlistcount' in session:
        return session['playlistcount']
    else:
#        session['playlistcount'] = db_session.query(func.count(Playlist.id).filter(Playlist.public).filter(Playlist.featured_video.isnot(None))).scalar()
        session['playlistcount'] = playlistcount_cache()
    return session['playlistcount']


def get_usercount():
    if 'usercount' in session:
        return session['usercount']
    else:
#        session['usercount'] =db_session.query(func.count(User.id).filter(User.public)).scalar()
        session['usercount'] = usercount_cache()
    return session['usercount']


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


def local_command(commands):
    for command in commands:
        localcmd = subprocess.Popen([command],
                                executable='/bin/bash',
                                shell = True,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE)
        result = localcmd.stdout.readlines()
        if not result:
            error = localcmd.stderr.readlines()
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
    vpn_conn = Vpn_conn(
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


@cache.cached(key_prefix="data"+"%s")
def videos_trending(PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).order_by(nullslast(Mv_Video.ac_views.desc())).limit(PER_PAGE).offset(offset))
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def videos_latest(PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset))
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def videos_newest(PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset))
#    videos = Mv_Video.query.order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset)
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def videos_popular(PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset))
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def channels_latest(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).limit(PER_PAGE).offset(offset))
#    channels = Mv_Channel.query.limit(PER_PAGE).offset(offset)
    channels = [r[0] for r in channel_values]
    return channels


@cache.cached(key_prefix="data"+"%s")
def channels_newest(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).order_by(Mv_Channel.ytc_publishedat.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset))
#    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_publishedat.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = [r[0] for r in channel_values]
    return channels

@cache.cached(key_prefix="data"+"%s")
def channels_popular(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).order_by(Mv_Channel.ytc_viewcount.desc()).limit(PER_PAGE).offset(offset))
#    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_viewcount.desc()).limit(PER_PAGE).offset(offset)
    channels = [r[0] for r in channel_values]
    return channels

@cache.cached(key_prefix="data"+"%s")
def channels_deleted(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset))
#    channels = Mv_Channel.query.filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = [r[0] for r in channel_values]
    return channels

@cache.cached(key_prefix="data"+"%s")
def channels_limited(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).order_by(Mv_Channel.limited.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset))
#    channels = Mv_Channel.query.order_by(Mv_Channel.limited.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = [r[0] for r in channel_values]
    return channels


@cache.cached(key_prefix="data"+"%s")
def channels_archived(PER_PAGE, offset):
    channel_values = db_session.execute(db_session.query(Mv_Channel).filter(Mv_Channel.ytc_archive).limit(PER_PAGE).offset(offset))
    channels = [r[0] for r in channel_values]
    return channels

@cache.memoize()
def channeli(ytc_id):
    channel = Mv_Channel.query.get(ytc_id)
    return channel


@cache.cached(key_prefix="data"+"%s"+"/channeli_videocount")
def channeli_videocount(ytc_id):
    channeli_videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(ytc_id=ytc_id).scalar()
    return channeli_videocount


@cache.cached(key_prefix="data"+"%s")
def channeli_videos_newest(ytc_id, PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc()).limit(PER_PAGE).offset(offset))
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def channeli_videos_popular(ytc_id, PER_PAGE, offset):
    video_values = db_session.execute(db_session.query(Mv_Video).filter_by(ytc_id=ytc_id).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset))
    videos = [r[0] for r in video_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def ytc_popular(ytc_id, PER_PAGE, offset):
    videos_values = db_session.execute(db_session.query(Mv_Video).filter_by(ytc_id=ytc_id).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset))
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
    videos = [r[0] for r in videos_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
#@cache.memoize()
def playlists_newest(PER_PAGE, offset):
    playlists_values = db_session.execute(db_session.query(Playlist).filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
                                          .order_by(Playlist.updated.desc()).limit(PER_PAGE).offset(offset))
#    playlists = Playlist.query.filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
#            .order_by(Playlist.updated.desc()).limit(PER_PAGE).offset(offset)
    playlists = [r[0] for r in playlists_values]
    return playlists
#
# does not work because object is lazy loaded, and i am not using the ORM and calling with the session object, because that causes the
# cannot pickle error message
#
# sqlalchemy.orm.exc.DetachedInstanceError: Parent instance <Playlist at 0x7f201f705600> is not bound to a Session;
# lazy load operation of attribute 'user' cannot proceed (Background on this error at: https://sqlalche.me/e/14/bhk3)
#

@cache.cached(key_prefix="data"+"%s")
#@cache.memoize()
def playlists_popular(PER_PAGE, offset):
#    playlists_values = db_session.execute(db_session.query(Playlist).filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
#                                          .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset))
    playlists = Playlist.query.filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
        .order_by(Playlist.updated.desc()).limit(PER_PAGE).offset(offset)
#    playlists = [r[0] for r in playlists_values]
    return playlists
#
# calling with the ORM and using the session object causes the 'cannot pickle session object' error message:
# _pickle.PicklingError: Can't pickle <class 'sqlalchemy.orm.session.Session'>: it's not the same object as sqlalchemy.orm.session.Session


@cache.memoize()
def playlisti(playlist):
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
    return playlist
#
# does not work because object is lazy loaded, and i am not using the ORM and calling with the session object, because that causes the
# cannot pickle error message
#
# sqlalchemy.orm.exc.DetachedInstanceError: Parent instance <Playlist at 0x7f201f705600> is not bound to a Session;
# lazy load operation of attribute 'user' cannot proceed (Background on this error at: https://sqlalche.me/e/14/bhk3)
#

#@cache.memoize()
@cache.cached(key_prefix="data"+"%s"+"/channeli_videocount")
def playlisti_videocount(playlist):
#    videocount = db_session.query(func.count(Mv_Video.id)).filter(Mv_Video.extractor_data.in_(playlist.videos)).scalar()
    playlisti_videocount = db_session.query(func.count(Mv_Video.id)).filter(Mv_Video.extractor_data.in_(playlist.videos)).scalar()
    print(playlisti_videocount)
    return playlisti_videocount
#
# sqlalchemy.orm.exc.DetachedInstanceError: Parent instance <Playlist at 0x7f201f705600> is not bound to a Session;
# lazy load operation of attribute 'user' cannot proceed (Background on this error at: https://sqlalche.me/e/14/bhk3)
#



@cache.cached(key_prefix="data"+"%s")
#@cache.memoize()
def playlisti_videos(playlist, ordering, PER_PAGE, offset):
#    playlisti_videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(playlist.videos)).order_by(ordering).limit(PER_PAGE).offset(offset)
    playlisti_values = db_session.execute(db_session.query(Mv_Video).filter(Mv_Video.extractor_data.in_(playlist.videos)).order_by(ordering).limit(PER_PAGE).offset(offset))
#    video_values = db_session.execute(db_session.query(Mv_Video).filter_by(ytc_id=ytc_id).order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset))

    videos = [r[0] for r in playlisti_values]
    return videos


@cache.cached(key_prefix="data"+"%s")
def users_newest(PER_PAGE, offset):
    users_values = db_session.execute(db_session.query(User).filter(User.public).order_by(User.id.desc()).limit(PER_PAGE).offset(offset))
#    users = User.query.filter(User.public).order_by(User.id.desc()).limit(PER_PAGE).offset(offset)
    users = [r[0] for r in users_values]
    return users


@cache.cached(key_prefix="data"+"%s")
def users_popular(PER_PAGE, offset):
    users_values = db_session.execute(db_session.query(User).filter(User.public).order_by(User.view_counter.desc()).limit(PER_PAGE).offset(offset))
#    users = User.query.filter(User.public).order_by(User.view_counter.desc()).limit(PER_PAGE).offset(offset)
    users = [r[0] for r in users_values]
    return users


@cache.cached(key_prefix="data"+"%s")
def useri(username):
    user = User.query.filter(func.lower(User.username) == func.lower(username)).scalar()
    return user


@cache.cached(key_prefix="data"+"%s"+"videocount")
def videocount_cache():
    videocount_cache = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    return videocount_cache


@cache.cached(key_prefix="data"+"%s"+"channelcount")
def channelcount_cache():
    channelcount_cache = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    #        session['channelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    return channelcount_cache


@cache.cached(key_prefix="data"+"%s"+"delchannelcount")
def delchannelcount_cache():
    delchannelcount_cache = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    #        session['delchannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    return delchannelcount_cache


@cache.cached(key_prefix="data"+"%s"+"archivechannelcount")
def archivechannelcount_cache():
    archivechannelcount_cache = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    #        session['archivechannelcount'] = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    return archivechannelcount_cache


@cache.cached(key_prefix="data"+"%s"+"playlistcount")
def playlistcount_cache():
    playlistcount_cache = db_session.query(func.count(Playlist.id).filter(Playlist.public).filter(Playlist.featured_video.isnot(None))).scalar()
    #        session['playlistcount'] = db_session.query(func.count(Playlist.id).filter(Playlist.public).filter(Playlist.featured_video.isnot(None))).scalar()
    return playlistcount_cache


@cache.cached(key_prefix="data"+"%s"+"usercount")
def usercount_cache():
    usercount_cache = db_session.query(func.count(User.id).filter(User.public)).scalar()
    #        session['usercount'] =db_session.query(func.count(User.id).filter(User.public)).scalar()
    return usercount_cache


@cache.memoize()
def navtabs_cache(locale):
    navtabs_cache = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, locale)).all()
#        row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
    return navtabs_cache


@cache.cached(key_prefix="data"+"%s"+"navtabs_index")
def navtabs_index_cache():
    navtabs_index_cache = db_session.query(Translation).with_entities(Translation.varname, Translation.en).all()
#    row = db_session.query(Translation).with_entities(Translation.varname, Translation.en).all()
    return navtabs_index_cache


def print_session():
    for k, v in session.items():
        print(k, v)


def get_video_files(item):
    extensions = ['webm', 'mp4', 'ogv', 'mkv']

    video_files = []
    for ext in extensions:
        for file in item.get_files(glob_pattern=f"*.{ext}"):
            video_files.append(file)

        if video_files:
            break

    return video_files


def check_video_files(ia_item):
    files_list = (ia_item.item_metadata['files'])
    extensionsToCheck = ['.webm', '.mp4', '.ogv', '.mkv']
    filename = None
    for x in files_list:
        if x['source']=='original' and any (ext in x['name'] for ext in extensionsToCheck):
            filename = (x.get("name"))
    return filename

def get_video_files_2(ia_item):
    files_list = (ia_item.item_metadata['files'])
    extensionsToCheck = ['.webm', '.mp4', '.ogv', '.mkv']
    filename = None
    for x in files_list:
        if x['source']=='original' and any (ext in x['name'] for ext in extensionsToCheck):
            filename = (x.get("name"))
    return filename

def get_image_file(ia_item):
    files_list = (ia_item.item_metadata['files'])
    image_extensionsToCheck = [".jpg", ".webp"]
    image_filename = None
    for x in files_list:
        if (
            x["source"] == "original"
            and (x["format"] != "Item Tile")
            and "Thumb" not in (x["format"])
            and any(ext in x["name"] for ext in image_extensionsToCheck)
        ):
            image_filename = x.get("name")
    if image_filename is None:
        for x in files_list:
            if x["name"] == "__ia_thumb.jpg":
                image_filename = x.get("name")
    return image_filename


def ac_object_exist(client, s3_bucket, itemname: str) -> bool:
    objects = client.list_objects(s3_bucket, prefix=itemname)
    if any(True for _ in objects):
        return True


def site_is_online(url, timeout=1):
    """Return True if the target URL is online.

    Raise an exception otherwise.
    """
    error = Exception("unknown error")
    parser = urlparse(url)
    host = parser.netloc or parser.path.split("/")[0]
    for port in (80, 443):
        connection = HTTPSConnection(host=host, port=port, timeout=timeout)
        try:
            connection.request("HEAD", "/")
            return True
        except Exception as e:
            error = e
        finally:
            connection.close()
#    raise error
    return False

def increment_video_counter(video_id, ip, header):
    entity_video = Entity.query.filter(Entity.extractor_data == video_id).scalar()
    today = str(datetime.date.today())
    myhash = hash(ip+header+today+str(entity_video.extractor_data))
    if Counter.query.filter(Counter.hash == myhash).scalar() is None:
        counter = Counter (hash=myhash)
        db_session.add(counter)

        if entity_video.ac_views is None:
            entity_video.ac_views = 0

        entity_video.ac_views = entity_video.ac_views + 1
        flag_modified(entity_video, "ac_views")
        db_session.commit()


def get_ia_item(extractor_data):
    IARCHIVEURL = current_app.config['IARCHIVEURL']
    global video_url
    if not video_url:
        ia_value = 'youtube-' + extractor_data
        ia_item = get_item(ia_value)
        if len(ia_item.item_metadata) == 0:
            VIDEOSERVER_URL = current_app.config['VIDEOSERVER_URL']
            video_url = f'{VIDEOSERVER_URL}unavailable/unavailable'
            return video_url
        full_filename = get_image_file(ia_item)
        filename = os.path.splitext(full_filename)[0]
        video_url = IARCHIVEURL + extractor_data + "/" + filename
        entity_video = Entity.query.filter(Entity.extractor_data == extractor_data).scalar()
        entity_video.thumbnail = full_filename
        flag_modified(entity_video, "ac_views")
        db_session.commit()
    return video_url