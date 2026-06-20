import datetime
import logging
import os
import re
import requests
import json
import base64

logger = logging.getLogger(__name__)

from datetime import timezone, timedelta
from flask_babelplus import lazy_gettext
from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify, abort)
from sqlalchemy import func, or_

from .database import db_session
from .models import MvChannel, User, Entity, Source, Sources_to_Videos, EmailList
from datatables import ColumnDT, DataTables
from threading import Thread

from . import util
from . import config
from .util import (
    confirm_token, send_all_mass_email, generate_confirmation_token,
    email_exists, email_list_exists, validate_user_email,
    ssh_command, local_command
)
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'htm', 'html', 'txt'}

_CHANNEL_ID_RE = re.compile(r'^UC[A-Za-z0-9_-]{22}$')
_SAFE_PARAM_RE = re.compile(r'^[A-Za-z0-9_-]{1,100}$')

_ALLOWED_CMD_NAMES = {
    'uptime', 'init 6', 'ls -lrt', 'df',
    'apt update -y && apt upgrade -y && apt autoremove -y',
    'backup', 'find', 'tubeup', 'systemctl',
}
_ALLOWED_ACTION_NAMES = {'status', 'stop', 'start', 'restart'}
_ALLOWED_SUBSYS_NAMES = {
    'archive_full', 'archive_full.timer', 'archive_full_run.timer',
    'archive_part', 'archive_part.timer', 'archive_part_run.timer',
    'archive_none', 'archive_none.timer', 'archive_none_run.timer',
    'find_archive', 'find_archive.timer', 'find_archive_run.timer',
    'channel_archive', 'channel_archive.timer', 'channel_archive_run.timer',
    'channel_archive_second', 'channel_archive_second.timer', 'channel_archive_second_run.timer',
    'channel_archive_third', 'channel_archive_third.timer', 'channel_archive_third_run.timer',
    'channel_archive_fourth', 'channel_archive_fourth.timer', 'channel_archive_fourth_run.timer',
    'channel_archive_part', 'channel_archive_part.timer', 'channel_archive_part_run.timer',
    'channel_archive_part_second', 'channel_archive_part_second.timer', 'channel_archive_part_second_run.timer',
    'channel_archive_part_third', 'channel_archive_part_third.timer', 'channel_archive_part_third_run.timer',
    'channel_archive_part_fourth', 'channel_archive_part_fourth.timer', 'channel_archive_part_fourth_run.timer',
    'pgsync', 'pgsync.timer', 'pgbackup', 'pgbackup.timer',
    'nginx', 'gunicorn', 'postgresql', 'imageproxy',
}
_SNS_CERT_URL_RE = re.compile(r'^https://sns\.[a-z0-9-]+\.amazonaws\.com/.*\.pem$')
_sns_cert_cache = {}

def _valid_channel_id(channel_id):
    return bool(channel_id and _CHANNEL_ID_RE.match(channel_id))

def _channel_playlist_url(channel_id):
    return "https://www.youtube.com/playlist?list=UU" + channel_id[2:]

def _valid_delta(delta):
    try:
        return int(delta) > 0
    except (ValueError, TypeError):
        return False

def _sns_signing_string(msg):
    if msg.get('Type') == 'SubscriptionConfirmation':
        keys = ['Message', 'MessageId', 'SubscribeURL', 'Timestamp', 'Token', 'TopicArn', 'Type']
    else:
        keys = ['Message', 'MessageId', 'Subject', 'Timestamp', 'TopicArn', 'Type']
    return ''.join(k + '\n' + msg[k] + '\n' for k in keys if k in msg).encode('utf-8')

def _verify_sns_signature(msg):
    cert_url = msg.get('SigningCertURL', '')
    if not _SNS_CERT_URL_RE.match(cert_url):
        return False
    try:
        if cert_url not in _sns_cert_cache:
            _sns_cert_cache[cert_url] = requests.get(cert_url, timeout=5).content
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
        from cryptography.hazmat.primitives import hashes
        cert = load_pem_x509_certificate(_sns_cert_cache[cert_url])
        sig = base64.b64decode(msg['Signature'])
        signing_str = _sns_signing_string(msg)
        hash_alg = hashes.SHA256() if msg.get('SignatureVersion') == '2' else hashes.SHA1()
        cert.public_key().verify(sig, signing_str, asym_padding.PKCS1v15(), hash_alg)
        return True
    except Exception:
        return False
url_orig = 'original_url'
sender = config.SES_EMAIL_SOURCE


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_mass_email(email, sender, subject, filename, service):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('newsletter/' + filename, confirm_url=confirm_url)
    Thread(target=send_all_mass_email, args=(email, sender, subject, html, service)).start()
    if email_exists(email):
        user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    else:
        user = db_session.query(EmailList).filter(func.lower(EmailList.email) == func.lower(email)).one()

    now = datetime.datetime.now(timezone.utc)
    user.email_lastsent_date = now
    db_session.add(user)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()


def db_unsubscribe_email(tablename, email, action):
    if tablename == 'User':
        user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    else:
        user = db_session.query(EmailList).filter(func.lower(EmailList.email) == func.lower(email)).one()
    now = datetime.datetime.now(timezone.utc)
    user.email_subscribed = False
    user.email_action = action
    user.updated = now
    db_session.add(user)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()


def db_add_email_list(email, email_source):
    now = datetime.datetime.now(timezone.utc)
    email_lastsent_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(30)
    username = email.split("@")[0]
    user = EmailList(
        email=email.lower(), username=username, email_source=email_source, \
        created_date=now, updated=now, email_lastsent_date=email_lastsent_date, \
        )
    db_session.add(user)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()


@bp.route('/')
@util.admin_login_required
def index():
    return render_template('admin/admin_index.html')


@bp.route('/channel_table')
@util.admin_login_required
def channel_table():
    data = request.args.get('data', 'data_all')
    return render_template('admin/admin_channel_table.html', data=data)


@bp.route('/channel_data_all')
@util.admin_login_required
def channel_data_all():
    columns = [
        ColumnDT(MvChannel.ytc_title),
        ColumnDT(MvChannel.ytc_id),
        ColumnDT(MvChannel.ytc_subscribercount),
        ColumnDT(MvChannel.ytc_viewcount),
        ColumnDT(MvChannel.total),
        ColumnDT(MvChannel.limited),
        ColumnDT(MvChannel.archive),
        ColumnDT(MvChannel.allow),
        ColumnDT(MvChannel.was_full),
        ColumnDT(func.to_char(MvChannel.delta,'dd')),
        ColumnDT(func.to_char(MvChannel.newest_video,'YYYY-mm-dd')),
        ColumnDT(func.to_char(MvChannel.ytc_publishedat,'YYYY-mm-dd')),
        ColumnDT(func.to_char(MvChannel.ytc_deleteddate,'YYYY-mm-dd')),
        ColumnDT(func.to_char(MvChannel.ytc_addeddate, 'YYYY-mm-dd')),
    ]

    query = db_session.query().select_from(MvChannel)
    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/video_table')
@util.admin_login_required
def video_table():
    ytc_id = request.args.get('ytc_id', 'None')
    return render_template('admin/admin_video_table.html', ytc_id=ytc_id)


@bp.route('/video_data')
@util.admin_login_required
def video_data():
    ytc_id = request.args.get('ytc_id', 'None')

    columns = [
        ColumnDT(Entity.extractor_data),
        ColumnDT(Entity.title),
        ColumnDT(Entity.views),
        ColumnDT(Entity.likes),
        ColumnDT(Entity.dislikes),
        ColumnDT(Entity.allow),
        ColumnDT(Entity.sync_ia),
        ColumnDT(Entity.exists_ia),
        ColumnDT(Entity.yt_deleted),
        ColumnDT(func.to_char(Entity.sync_iadate, 'YYYY-mm-dd')),
        ColumnDT(func.to_char(Entity.addeddate, 'YYYY-mm-dd')),
    ]

    if ytc_id == "all":
        query = db_session.query().select_from(Entity)

    else:
        query = db_session.query(). \
            select_from(Entity). \
            join(Sources_to_Videos). \
            join(Source). \
            filter(Source.ytc_id == ytc_id)

    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/channel_table_new')
@util.admin_login_required
def channel_table_new():
    return render_template('admin/admin_channel_table_new.html')


@bp.route('/channel_table_new_data')
@util.admin_login_required
def channel_table_new_data():
    query = db_session.query(MvChannel).filter(MvChannel.ytc_deleted == False)

    # search filter
    search = request.args.get('search')
    if search:
        query = query.filter(or_(
            MvChannel.ytc_id.ilike(f'%{search}%'),
            MvChannel.ytc_title.ilike(f'%{search}%')
        ))

    total = query.count()

    # sorting
    sort = request.args.get('sort')
    if sort:
        order = []
        for s in sort.split(','):
            direction = s[0]
            name = s[1:]
            if name not in ['ytc_videocount', 'total', 'archived', 'limited', 'newest', 'updated',
                            'delta', 'allow', 'ytc_archive', 'ytc_partarchive', 'was_full', 'was_part']:
                name = 'name'
            col = getattr(MvChannel, name)
            if direction == '-':
                col = col.desc()
            order.append(col)
        if order:
            query = query.order_by(*order)

    # pagination
    start = request.args.get('start', type=int, default=-1)
    length = request.args.get('length', type=int, default=-1)
    if start != -1 and length != -1:
        query = query.offset(start).limit(length)

    # response
    return {
        'data': [source.to_dict() for source in query],
        'total': total,
    }


@bp.route('/channel_table_new_data', methods=['POST'])
@util.admin_login_required
def update():
    data = request.get_json()
    if 'id' not in data:
        abort(400)
    source = db_session.get(Source, (data['id']))
    for field in ['ytc_title']:
        if field in data:
            setattr(source, field, data[field])
    #
    # boolean fields must be converted from text to string
    #
    for field in ['allow', 'ytc_archive', 'ytc_partarchive']:
        if field in data:
            bool_field = util.string_boolean(data[field])
            setattr(source, field, bool_field)
    #
    # delta is a timestamp and must be tweaked
    #
    for field in ['delta']:
        if field in data:
            intdays = int(data[field])
            delta = timedelta(days=intdays)
            setattr(source, field, delta)

    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        return '', 500
    return '', 204


@bp.route('/add_channel', methods=['GET', 'POST'])
@util.admin_login_required
def add_channel():
    title = request.args.get('title', 'Add')
    ddays = request.args.get('ddays', '5')
    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        delta = (request.form['delta'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title, ddays=ddays)
        if not _valid_delta(delta):
            flash('Invalid delta value', 'error')
            return render_template('admin/admin_channels.html', title=title, ddays=ddays)
        action = ' afs '
        channel_url = _channel_playlist_url(channel_id)

        params1 = ' yt-syncac '
        params2 = ' -delta '
        params3 = ' > $HOME/nohup_ssh.out 2>&1 &'

        command = params1 + action + channel_url + params2 + delta + params3
        commands = [command]
        try:
            local_command(commands)
            flash(channel_id + " added using afs")
        except Exception:
            logger.exception("local_command failed for add_channel channel_id=%s", channel_id)
            flash(channel_id + " NOT added using afs")

    return render_template('admin/admin_channels.html', title=title, ddays=ddays)


@bp.route('/update_channel', methods=['GET', 'POST'])
@util.admin_login_required
def update_channel():
    title = request.args.get('title', 'Update')
    atype = request.args.get('atype', 'partial')
    ddays = request.args.get('ddays', '')

    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        delta = (request.form['delta'])
        archive_type = (request.form['archive_type'])
        deleted = (request.form['deleted'])
        viewcount = (request.form['viewcount'])
        subscribercount = (request.form['subscribercount'])
        deleteddate = (request.form['deleteddate'])

        if delta:
            intdays = int(delta)
            delta = timedelta(days=intdays)

        if deleted:
            deleted = util.str_to_bool(deleted)

        if util.channel_update(channel_id, delta, archive_type, deleted, viewcount, subscribercount, deleteddate):
            flash(channel_id + ' Updated', 'success')
        else:
            flash(channel_id + ' NOT Updated', 'error')

        return redirect(request.url)


    return render_template('admin/admin_channels.html', title=title, ddays=ddays, atype=atype)


@bp.route('/enable_channel', methods=['GET', 'POST'])
@util.admin_login_required
def enable_channel():
    title = "Enable"
    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(channel_id)
        action = ' enable '

        params1 = ' yt-syncac '
        params2 = ' > $HOME/nohup_ssh.out 2>&1 &'

        command = params1 + action + channel_url + params2
        commands = [command]
        try:
            local_command(commands)
            flash(channel_id + ' enable dispatched', 'success')
        except Exception:
            logger.exception("local_command failed for enable_channel channel_id=%s", channel_id)
            flash(channel_id + ' enable FAILED', 'error')
    return render_template('admin/admin_channels.html', title=title)


@bp.route('/disable_channel', methods=['GET', 'POST'])
@util.admin_login_required
def disable_channel():
    title = "Disable"
    ytc_id = request.args.get('ytc_id', None)
    if request.method == 'POST' or ytc_id is not None:
        if not ytc_id:
            ytc_id = (request.form['channel_id'])
        if not _valid_channel_id(ytc_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(ytc_id)
        action = ' disable '

        params1 = ' yt-syncac '
        params2 = ' > $HOME/nohup_ssh.out 2>&1 &'

        command = params1 + action + channel_url + params2
        commands = [command]
        try:
            local_command(commands)
            flash(ytc_id + ' disable dispatched', 'success')
        except Exception:
            logger.exception("local_command failed for disable_channel ytc_id=%s", ytc_id)
            flash(ytc_id + ' disable FAILED', 'error')
    return render_template('admin/admin_channels.html', title=title)


@bp.route('/resync_channel', methods=['GET', 'POST'])
@util.admin_login_required
def resync_channel():
    title = "Resync"
    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(channel_id)
        action = ' resync '

        params1 = ' yt-syncac '
        params2 = ' > $HOME/nohup_ssh.out 2>&1 &'

        command = params1 + action + channel_url + params2
        commands = [command]
        try:
            local_command(commands)
            flash(channel_id + ' resync dispatched', 'success')
        except Exception:
            logger.exception("local_command failed for resync_channel channel_id=%s", channel_id)
            flash(channel_id + ' resync FAILED', 'error')
    return render_template('admin/admin_channels.html', title=title)


@bp.route('/remove_channel', methods=['GET', 'POST'])
@util.admin_login_required
def remove_channel():
    title = "Remove"
    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(channel_id)
        action = ' remove '

        params1 = ' yt-syncac '
        params2 = ' > $HOME/nohup_ssh.out 2>&1 &'

        command = params1 + action + channel_url + params2
        commands = [command]
        try:
            local_command(commands)
            flash(channel_id + ' remove dispatched', 'success')
        except Exception:
            logger.exception("local_command failed for remove_channel channel_id=%s", channel_id)
            flash(channel_id + ' remove FAILED', 'error')

    return render_template('admin/admin_channels.html', title=title)


@bp.route('/mirror_channel', methods=['GET', 'POST'])
@util.admin_login_required
def mirror_channel():
    title = "Mirror"
    if request.method == 'POST':
        sys_name = current_app.config['AC_SSH_HOST']
        s3_user = current_app.config['AC_S3_USER']
        channel_id = (request.form['channel_id'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        if not sys_name:
            flash('AC_SSH_HOST not configured', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(channel_id)
        action = 'mirror '
        cookie = '-cf $IA_COOKIES '
        resync = '-ur -i '

        inner = "yt-syncac " + action + channel_url + " " + cookie + resync + "-f"
        command = "nohup bash -c 'set -a && . /opt/altcen/altcensored.env && set +a && " + inner + "' > /root/nohup_ssh.out 2>&1 &"
        commands = [command]
        try:
            ssh_command(sys_name, commands, s3_user)
            flash(channel_id + ' mirror dispatched', 'success')
        except Exception:
            logger.exception("ssh_command failed for mirror_channel channel_id=%s", channel_id)
            flash(channel_id + ' mirror FAILED', 'error')

    return render_template('admin/admin_channels.html', title=title)


@bp.route('/status_channel', methods=['GET', 'POST'])
@util.admin_login_required
def status_channel():
    title = "Status"
    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        if not _valid_channel_id(channel_id):
            flash('Invalid channel ID', 'error')
            return render_template('admin/admin_channels.html', title=title)
        channel_url = _channel_playlist_url(channel_id)
        action = ' status '
        params1 = ' yt-syncac -q '

        command = params1 + action + channel_url
        commands = [command]
        local_command(commands, timeout=120)

        return render_template('admin/admin_messages.html')

    return render_template('admin/admin_channels.html', title=title)


@bp.route('/update_video', methods=['GET', 'POST'])
@util.admin_login_required
def update_video():
    title = "Update Video"
    if request.method == 'POST':
        video_id = (request.form['video_id'])

        if request.form['allow_action']:
            bool_allow = util.string_boolean(request.form['allow_action'])
        else:
            bool_allow = None

        if request.form['deleted_action']:
            bool_deleted = util.string_boolean(request.form['deleted_action'])
        else:
            bool_deleted = None

        if util.video_toggle_allow(video_id, bool_allow, bool_deleted):
            flash(video_id + ' allow/deleted toggled', 'success')
        else:
            flash(video_id + ' allow NOT toggled', 'error')

    return render_template('admin/admin_videos.html', title=title)


@bp.route('/system_commands', methods=['GET', 'POST'])
@util.admin_login_required
def system_commands():
    title = "System Commands"
    if request.method == 'POST':
        sys_name = (request.form['sys_name'])
        cmd_name = (request.form['cmd_name'])
        subsys_name = (request.form['subsys_name'])
        action_name = (request.form['action_name'])
        param_name = (request.form['param_name'])
        find_run = (request.form['find_run'])

        if cmd_name not in _ALLOWED_CMD_NAMES:
            flash('Invalid command', 'error')
            return render_template('admin/admin_system_commands.html', title=title)
        if cmd_name == 'systemctl':
            if action_name not in _ALLOWED_ACTION_NAMES:
                flash('Invalid action', 'error')
                return render_template('admin/admin_system_commands.html', title=title)
            if subsys_name not in _ALLOWED_SUBSYS_NAMES:
                flash('Invalid subsystem', 'error')
                return render_template('admin/admin_system_commands.html', title=title)
        if cmd_name in ('find', 'tubeup') and param_name and not _SAFE_PARAM_RE.match(param_name):
            flash('Invalid parameter — only alphanumeric, hyphens and underscores allowed', 'error')
            return render_template('admin/admin_system_commands.html', title=title)

        find_cmd = '/opt/altcen/find_archive.py'
        bground_p1 = 'nohup '
        bground_p2 = ' > /root/nohup_ssh.out 2>&1 &'
        find_p1 = " -s "
        find_p2 = " -d 7000 -v 1"
        tubeup_p = ' --metadata=collection:altcensored --cookies=/home/m2np3/rocketfuel_cookies.txt ' \
                   '--proxy=socks5://127.0.0.1:5080 https://www.youtube.com/watch?v='

        if cmd_name == 'systemctl':
            command = cmd_name + " " + action_name + " " + subsys_name
        elif cmd_name == 'find':
            command = find_cmd + find_p1 + param_name + find_p2
            if find_run == 'true':
                command = bground_p1 + command + ' -r' + bground_p2
        elif cmd_name == 'tubeup':
            command = bground_p1 + cmd_name + tubeup_p + param_name + bground_p2
        else:
            command = cmd_name

        commands = [command]
        local_command(commands)

        return render_template('admin/admin_messages.html')

    return render_template('admin/admin_system_commands.html', title=title)



@bp.route('/scraper_status')
@util.admin_login_required
def scraper_status():
    commands = ["systemctl status 5080@sync_archivenone",
                "systemctl status 5080@upload_archivelatest",
                "systemctl status 5080@upload_archivepart",
                "systemctl status 5080@upload_archivefull",
                "systemctl status 5080@upload_archivepart_firstrun",
                "systemctl status 5080@upload_archivefull_firstrun",
                "systemctl status 3proxy",
                "journalctl -n -u find_archive",
                "systemctl status pgbackup",
                "systemctl status pgsync",
                "journalctl -u gunicorn -n 20",
                "systemctl status",
                "systemctl --failed",
                "df /dev/sda1",
                "awk '{print $3}' /var/log/nginx/rt_cache.log  | sort | uniq -c | sort -r",
                "du -c -h -s /var/cache/nginx/i_cache",
                "du -c -h -s /var/cache/nginx/f_cache"
                ]
    local_command(commands)
    return render_template('admin/admin_messages.html')


@bp.route('/mass_email', methods=['GET', 'POST'])
@util.admin_login_required
def mass_email():
    title = "Send Mass Email"

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if not (file and allowed_file(file.filename)):
            flash('Invalid or missing file', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        folder = current_app.root_path + config.UPLOAD_FOLDER
        file.save(os.path.join(folder, filename))

        service = (request.form['service'])
        recipients = (request.form['recipients'])
        sendlimit = (request.form['sendlimit'])
        language = (request.form['language'])
        subject = (request.form['subject'])
        dayslastsent = int((request.form['dayslastsent']))
        testonly = (request.form['testonly'])

        if recipients == 'verified':
            usercount = db_session.query(func.count(User.id)). \
                filter((User.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(User.settings['locale'].as_string() == language). \
                filter(User.email_verified). \
                filter(User.email_subscribed). \
                scalar()
            users = db_session.query(User). \
                filter((User.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(User.settings['locale'].as_string() == language). \
                filter(User.email_subscribed). \
                filter(User.email_verified). \
                order_by(func.random()). \
                limit(sendlimit).all()

        elif recipients == 'subscribed':
            usercount = db_session.query(func.count(User.id)). \
                filter((User.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(User.settings['locale'].as_string() == language). \
                filter(User.email_subscribed). \
                scalar()
            users = db_session.query(User). \
                filter((User.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(User.settings['locale'].as_string() == language). \
                filter(User.email_subscribed). \
                order_by(func.random()). \
                limit(sendlimit).all()

        elif recipients == 'friends':
            usercount = db_session.query(func.count(EmailList.id)). \
                filter((EmailList.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(EmailList.email_subscribed). \
                scalar()
            users = db_session.query(EmailList). \
                filter((EmailList.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(EmailList.email_subscribed). \
                order_by(func.random()). \
                limit(sendlimit).all()

        elif recipients == 'admin':
            email = 'admin@altcensored.com'
            send_mass_email(email, sender, subject, filename, service)
            flash(email)
            return redirect(url_for('admin.index'))

        else:
            flash('Unknown recipients value: ' + recipients, 'error')
            return redirect(request.url)

        flash(usercount)
        flash('test only : ' + testonly)
        for user in users:
            if testonly == 'false':
                send_mass_email(user.email, sender, subject, filename, service)
                flash(user.email)

        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
        return redirect(url_for('admin.index'))

    return render_template('admin/admin_mass_email.html', title=title)


@bp.route('/update_bounce', methods=['GET', 'POST'])
@util.admin_login_required
def update_bounce():
    title = "Upload altcen_user Bounce File"
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            folder = current_app.root_path + config.UPLOAD_FOLDER
            folder_file = folder + '/' + filename
            file.save(os.path.join(folder, filename))

            action = "sgrid_bounce"
            with open(folder_file) as file:
                for email in file:
                    email = (email.rstrip())
                    try:
                        tablename = 'User' if email_exists(email) else 'EmailList'
                        db_unsubscribe_email(tablename, email, action)
                        flash(email)
                    except Exception:
                        logger.exception("db_unsubscribe_email failed for email=%s", email)
                        flash(email + ' NOT UNSUBSCRIBED')

            return redirect(url_for('admin.index'))

    return render_template('admin/admin_mass_email.html', title=title)


@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def unsubscribe_email(token):
    email = confirm_token(token, 86400)
    l_msg = lazy_gettext('Unsubscribe')+' '
    item_quoted = (f'"{email}"')
    message = l_msg + ' ' + item_quoted + '?'

    if email == False:
        conf = lazy_gettext('The unsubscribe link is invalid')
        flash(conf, 'error')
        return redirect(url_for('video.index'))
    else:
        if email_exists(email):
            user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
        else:
            user = db_session.query(EmailList).filter(func.lower(EmailList.email) == func.lower(email)).one()

        if not user.email_subscribed:
            conf = item_quoted + ' ' + lazy_gettext('has already been unsubscribed')
            flash(conf, 'error')
            return redirect(url_for('video.index'))

    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            if email_exists(email):
                user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
                tablename = 'User'
            else:
                user = db_session.query(EmailList).filter(func.lower(EmailList.email) == func.lower(email)).one()
                tablename = 'EmailList'
            action = 'altc_unsub'
            db_unsubscribe_email(tablename, user.email, action)
            conf = item_quoted + ' ' + lazy_gettext('was unsubscribed')
            flash(conf, 'success')
            return redirect(url_for('video.index'))
        else:
            conf = item_quoted + ' ' + lazy_gettext('was NOT unsubscribed')
            flash(conf, 'error')
            return redirect(request.args.get(url_orig, '/'))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/aws_bounce', methods=['GET', 'POST', 'PUT'])
def aws_bounce():
    # AWS sends JSON with text/plain mimetype
    try:
        js = json.loads(request.data)
    except json.JSONDecodeError:
        return 'OK\n'

    if not _verify_sns_signature(js):
        abort(400)

    hdr = request.headers.get('X-Amz-Sns-Message-Type')

    # subscribe to the SNS topic
    if hdr == 'SubscriptionConfirmation' and 'SubscribeURL' in js:
        r = requests.get(js['SubscribeURL'])

    if hdr == 'Notification':
        try:
            msg = js["Message"]
            msgjs = json.loads(msg)
            email = msgjs["bounce"]["bouncedRecipients"][0]["emailAddress"]
            action = 'aws_bounce'

            if email_exists(email):
                tablename = 'User'
            elif email_list_exists(email):
                tablename = 'EmailList'
            else:
                logger.warning("aws_bounce: email not found in either table: %s", email)
                return 'OK\n'

            db_unsubscribe_email(tablename, email, action)
        except Exception:
            logger.exception("aws_bounce: failed to process notification")

    return 'OK\n'


@bp.route('/aws_complaint', methods=['GET', 'POST'])
def aws_complaint():
    # AWS sends JSON with text/plain mimetype
    try:
        js = json.loads(request.data)
    except json.JSONDecodeError:
        return 'OK\n'

    if not _verify_sns_signature(js):
        abort(400)

    hdr = request.headers.get('X-Amz-Sns-Message-Type')

    # subscribe to the SNS topic
    if hdr == 'SubscriptionConfirmation' and 'SubscribeURL' in js:
        r = requests.get(js['SubscribeURL'])

    if hdr == 'Notification':
        try:
            msg = js["Message"]
            msgjs = json.loads(msg)
            email = msgjs["complaint"]["complainedRecipients"][0]["emailAddress"]
            action = 'aws_complaint'

            if email_exists(email):
                tablename = 'User'
            elif email_list_exists(email):
                tablename = 'EmailList'
            else:
                logger.warning("aws_complaint: email not found in either table: %s", email)
                return 'OK\n'

            db_unsubscribe_email(tablename, email, action)
        except Exception:
            logger.exception("aws_complaint: failed to process notification")

    return 'OK\n'


@bp.route('/add_email_list', methods=['GET', 'POST'])
@util.admin_login_required
def add_email_list():
    title = "Upload Email List File"
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            folder = current_app.root_path + config.UPLOAD_FOLDER
            folder_file = folder + '/' + filename
            file.save(os.path.join(folder, filename))

            email_source = (request.form['email_source'])

            with open(folder_file) as file:
                for email in file:
                    email = (email.rstrip())

                    now = datetime.datetime.now(timezone.utc)
                    username = email.split("@")[0]

                    if email_exists(email):
                        flash(email + ' NOT ADDED, already in altcen_user')
                    elif email_list_exists(email):
                        flash(email + ' NOT ADDED, in email_list')
                    elif validate_user_email(email):
                        flash(email + ' NOT ADDED, invalid syntax')
                    else:
                        db_add_email_list(email, email_source)
                        flash(email + ' added')

            return redirect(url_for('admin.index'))

    return render_template('admin/admin_mass_email.html', title=title)



