import os
import datetime
import requests
import json
import time

from datetime import timezone, timedelta
from flask_babelplus import lazy_gettext
from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify, abort)
from sqlalchemy import func
from .database import db_session
from .models import Mv_Channel, User, Entity, Source, Sources_to_Videos, Email_list
from datatables import ColumnDT, DataTables
from threading import Thread

from . import util
from . import config
from .util import (
    confirm_token, send_all_mass_email, generate_confirmation_token,
    email_exists, email_list_exists, validate_user_email,
    channel_partial_add, channel_full_add, ssh_command, local_command,
    channel_partial_remove, channel_full_remove
)
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'htm', 'html', 'txt'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_mass_email(email, subject, filename, service):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('newsletter/' + filename, confirm_url=confirm_url)
    Thread(target=send_all_mass_email, args=(email, subject, html, service)).start()
    if email_exists(email):
        user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    else:
        user = db_session.query(Email_list).filter(func.lower(Email_list.email) == func.lower(email)).one()

    now = datetime.datetime.now(timezone.utc)
    user.email_lastsent_date = now
    db_session.add(user)


def db_unsubscribe_email(tablename, email, action):
    if tablename == 'User':
        user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    else:
        user = db_session.query(Email_list).filter(func.lower(Email_list.email) == func.lower(email)).one()
    now = datetime.datetime.now(timezone.utc)
    user.email_subscribed = False
    user.email_action = action
    user.updated = now
    db_session.add(user)
    db_session.commit()


def db_add_email_list(email, email_source):
    now = datetime.datetime.now(timezone.utc)
    email_lastsent_date = datetime.datetime.now(timezone.utc) - datetime.timedelta(30)
    username = email.split("@")[0]
    user = Email_list(
        email=email.lower(), username=username, email_source=email_source, \
        created_date=now, updated=now, email_lastsent_date=email_lastsent_date, \
        )
    db_session.add(user)
    db_session.commit()


@bp.route('/')
@util.login_required
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
        ColumnDT(Mv_Channel.ytc_title),
        ColumnDT(Mv_Channel.ytc_id),
        ColumnDT(Mv_Channel.ytc_subscribercount),
        ColumnDT(Mv_Channel.ytc_viewcount),
        ColumnDT(Mv_Channel.total),
        ColumnDT(Mv_Channel.limited),
        ColumnDT(Mv_Channel.allow),
        ColumnDT(func.to_char(Mv_Channel.delta, 'DDD')),
        ColumnDT(Mv_Channel.ytc_partarchive),
        ColumnDT(Mv_Channel.ytc_archive),
        ColumnDT(func.to_char(Mv_Channel.ytc_publishedat, 'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_deleteddate, 'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_addeddate, 'YYYY-mm-dd')),
    ]

    query = db_session.query().select_from(Mv_Channel)
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


@bp.route('/add_channel', methods=['GET', 'POST'])
@util.admin_login_required
def add_channel():
    title = request.args.get('title', 'Add')
    ddays = request.args.get('ddays', '')
    if request.method == 'POST':
        sys_name = 'scraper'
        channel_id = (request.form['channel_id'])
        action = 'afs'
        delta = (request.form['delta'])
        channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])

        params1 = 'ALTC_DATABASE_URL=' + config.SQLALCHEMY_DATABASE_URI
        params2 = ' nohup youtube-sync -p /home/m2np3/m2np3 --proxy socks5://127.0.0.1:5080 --cookies /home/m2np3/rocketfuel_cookies.txt '
        params3 = ' -delta '
        params4 = ' > /root/nohup_ssh.out 2>&1 &'

        command = params1 + params2 + action + " " + channel_url + params3 + delta + params4
        commands = [command]
        try:
#            ssh_command(sys_name, commands)
            local_command(commands)
            flash(channel_id + " added using afs")
        except:
            flash(channel_id + " NOT added usiing afs")

    return render_template('admin/admin_channels.html', title=title, ddays=ddays)


@bp.route('/update_channel', methods=['GET', 'POST'])
@util.admin_login_required
def update_channel():
    title = request.args.get('title', 'Update')
    atype = request.args.get('atype', 'null')
    ddays = request.args.get('ddays', '')

    if request.method == 'POST':
        channel_id = (request.form['channel_id'])
        delta = (request.form['delta'])
        archive_type = (request.form['archive_type'])
        deleted = (request.form['deleted'])
        channel_tables = (request.form['channel_tables'])
        viewcount = (request.form['viewcount'])
        subscribercount = (request.form['subscribercount'])
        deleteddate = (request.form['deleteddate'])

        print(archive_type)

        if delta:
            intdays = int(delta)
            delta = timedelta(days=intdays)

        if deleted:
            deleted = util.str_to_bool(deleted)

        if channel_tables:
            if channel_tables == 'add_partial':
                if channel_partial_add(channel_id):
                    flash(channel_id + ' ALREADY EXIST for partial archiving', 'success')
                else:
                    flash(channel_id + ' ADDED for partial archiving', 'error')

            elif channel_tables == 'add_full':
                channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
                if channel_full_add(channel_url):
                    flash(channel_url + ' ALREADY EXIST for full archiving', 'error')
                else:
                    flash(channel_url + ' ADDED for full archiving', 'success')

            elif channel_tables == 'remove_partial':
                if channel_partial_remove(channel_id):
                    flash(channel_id + ' DOES NOT EXIST for partial archiving', 'error')
                else:
                    flash(channel_id + ' REMOVED from partial archiving', 'success')

            elif channel_tables == 'remove_full':
                channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
                if channel_full_remove(channel_url):
                    flash(channel_url + ' DOES NOT EXIST for full archiving', 'error')
                else:
                    flash(channel_url + ' REMOVED from full archiving', 'success')


        if util.channel_update(channel_id, delta, archive_type, deleted, viewcount, subscribercount, deleteddate):
            flash(channel_id + ' Updated', 'success')
        else:
            flash(channel_id + ' NOT Updated', 'error')

        return redirect(request.url)


    return render_template('admin/admin_channels.html', title=title, ddays=ddays, atype=atype)


@bp.route('/disable_channel', methods=['GET', 'POST'])
@util.admin_login_required
def disable_channel():
    title = "Disable"
    if request.method == 'POST':
        sys_name = 'scraper'
        channel_id = (request.form['channel_id'])
        channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
        action = 'disable'

        params1 = 'ALTC_DATABASE_URL=' + config.SQLALCHEMY_DATABASE_URI
        params2 = ' youtube-sync -p /home/m2np3/m2np3 --proxy socks5://127.0.0.1:5080 '
        params3 = ' > /root/nohup_ssh.out 2>&1 &'

        command = params1 + params2 + action + " " + channel_url + params3
        commands = [command]
#        ssh_command(sys_name, commands)
        local_command(commands)
    return render_template('admin/admin_channels.html', title=title)


@bp.route('/remove_channel', methods=['GET', 'POST'])
@util.admin_login_required
def remove_channel():
    title = "Remove"
    if request.method == 'POST':
        sys_name = 'scraper'
        channel_id = (request.form['channel_id'])
        channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
        action = 'remove'

        params1 = 'ALTC_DATABASE_URL=' + config.SQLALCHEMY_DATABASE_URI
        params2 = ' youtube-sync -p /home/m2np3/m2np3 --proxy socks5://127.0.0.1:5080 '
        params3 = ' > /root/nohup_ssh.out 2>&1 &'

        command = params1 + params2 + action + " " + channel_url + params3
        commands = [command]
#        ssh_command(sys_name, commands)
        local_command(commands)

        if channel_partial_remove(channel_id):
            flash(channel_id + ' DOES NOT EXIST for partial archiving', 'error')
        else:
            flash(channel_id + ' REMOVED from partial archiving', 'success')

        if channel_full_remove(channel_url):
            flash(channel_url + ' DOES NOT EXIST for full archiving', 'error')
        else:
            flash(channel_url + ' REMOVED from full archiving', 'success')

    return render_template('admin/admin_channels.html', title=title)


@bp.route('/resync_channel', methods=['GET', 'POST'])
@util.admin_login_required
def resync_channel():
    title = "Resync"
    if request.method == 'POST':
        sys_name = 'scraper'
        channel_id = (request.form['channel_id'])
        channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
        action = 'resync_all'

        params1 = 'ALTC_DATABASE_URL=' + config.SQLALCHEMY_DATABASE_URI
        params2 = ' nohup youtube-sync -p /home/m2np3/m2np3 --proxy socks5://127.0.0.1:5080 --cookies /home/m2np3/rocketfuel_cookies.txt '
        params3 = ' -f > /root/nohup_ssh.out 2>&1 &'

        command = params1 + params2 + action + " " + channel_url + params3
        commands = [command]
#        ssh_command(sys_name, commands)
        local_command(commands)

    return render_template('admin/admin_channels.html', title=title)


@bp.route('/status_channel', methods=['GET', 'POST'])
@util.admin_login_required
def status_channel():
    title = "Status"
    if request.method == 'POST':
        sys_name = 'scraper'
        channel_id = (request.form['channel_id'])
        channel_url = "https://www.youtube.com/playlist?list=UU" + (channel_id[2:])
        action = 'status_short'

        params1 = 'ALTC_DATABASE_URL=' + config.SQLALCHEMY_DATABASE_URI
        params2 = ' youtube-sync -p /home/m2np3/m2np3 --proxy socks5://127.0.0.1:5080 '
        command = params1 + params2 + action + " " + channel_url
        commands = [command]
#        ssh_command(sys_name, commands)
        local_command(commands)

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

        find_cmd = '/home/m2np3/channel_find/find_archive.py'
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
#        ssh_command(sys_name, commands)
        local_command(commands)

        return render_template('admin/admin_messages.html')

    return render_template('admin/admin_system_commands.html', title=title)



@bp.route('/scraper_status')
@util.admin_login_required
def scraper_status():
#    sys_name = 'web'
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
                "df /dev/sda1",
                "du -c -h -s /var/cache/nginx/i_cache",
                "du -c -h -s /var/cache/nginx/f_cache",
                "journalctl -u gunicorn -n 20",
                "systemctl --failed",
                "systemctl status"
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
        if file and allowed_file(file.filename):
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

        if recipients == 'subscribed':
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

        if recipients == 'friends':
            usercount = db_session.query(func.count(Email_list.id)). \
                filter((Email_list.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(Email_list.email_subscribed). \
                scalar()
            users = db_session.query(Email_list). \
                filter((Email_list.email_lastsent_date) < func.current_date() - dayslastsent). \
                filter(Email_list.email_subscribed). \
                order_by(func.random()). \
                limit(sendlimit).all()

        if recipients == 'admin':
            usercount = '1'
            email = 'admin@altcensored.com'
            send_mass_email(email, subject, filename, service)
            flash(email)
            return redirect(url_for('admin.index'))

        flash(usercount)
        flash('test only : ' + testonly)
        for user in users:
            if testonly == 'false':
                send_mass_email(user.email, subject, filename, service)
                flash(user.email)

        db_session.commit()
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
                        db_unsubscribe_email(email, action)
                        flash(email)
                    except:
                        flash(email + ' NOT UNSUBSCRIBED')

            return redirect(url_for('admin.index'))

    return render_template('admin/admin_mass_email.html', title=title)


@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def unsubscribe_email(token):
    email = confirm_token(token, None)
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
            user = db_session.query(Email_list).filter(func.lower(Email_list.email) == func.lower(email)).one()

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
                user = db_session.query(Email_list).filter(func.lower(Email_list.email) == func.lower(email)).one()
                tablename = 'Email_list'
            action = 'altc_unsub'
            db_unsubscribe_email(tablename, user.email, action)
            conf = item_quoted + ' ' + lazy_gettext('was unsubscribed')
            flash(conf, 'success')
            return redirect(url_for('video.index'))
        else:
            conf = item_quoted + ' ' + lazy_gettext('was NOT unsubscribed')
            flash(conf, 'error')
            return redirect(request.args.get('original_url', '/'))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/aws_bounce', methods=['GET', 'POST', 'PUT'])
def aws_bounce():
    # AWS sends JSON with text/plain mimetype
    try:
        js = json.loads(request.data)
    except:
        pass

    hdr = request.headers.get('X-Amz-Sns-Message-Type')

    # subscribe to the SNS topic
    if hdr == 'SubscriptionConfirmation' and 'SubscribeURL' in js:
        r = requests.get(js['SubscribeURL'])

    if hdr == 'Notification':
        msg = js["Message"]
        msgjs = json.loads(msg)

        email = msgjs["bounce"]["bouncedRecipients"][0]["emailAddress"]
        action = 'aws_bounce'  # unenforced code for aws bounce

        if email_exists(email):
            user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
            tablename = 'User'
        else:
            tablename = 'Email_list'

        db_unsubscribe_email(tablename, email, action)

    return 'OK\n'


@bp.route('/aws_complaint', methods=['GET', 'POST'])
def aws_complaint():
    # AWS sends JSON with text/plain mimetype
    try:
        js = json.loads(request.data)
    except:
        pass

    hdr = request.headers.get('X-Amz-Sns-Message-Type')

    # subscribe to the SNS topic
    if hdr == 'SubscriptionConfirmation' and 'SubscribeURL' in js:
        r = requests.get(js['SubscribeURL'])

    if hdr == 'Notification':
        msg = js["Message"]
        msgjs = json.loads(msg)

        email = msgjs["complaint"]["complainedRecipients"][0]["emailAddress"]
        action = 'aws_complaint'  # unenforced code for aws complaint

        if email_exists(email):
            user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
            tablename = 'User'
        else:
            tablename = 'Email_list'

        db_unsubscribe_email(tablename, email, action)

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


@bp.route('/test', methods=['GET', 'POST'])
def add_message():
    type = request.headers.get('Content-Type')

    if type == 'application/json':
        content = request.json
        return content

    elif type == 'text/html':

        js = json.loads(request.data)
        msg = js["Message"]
        msgjs = json.loads(msg)

        #        emailbounce = msgjs["bounce"]["bouncedRecipients"][0]["emailAddress"]
        emailcomplaint = msgjs["complaint"]["complainedRecipients"][0]["emailAddress"]

        #        folder = current_app.root_path + config.UPLOAD_FOLDER
        #        myfile = 'email_add'
        #        with open(os.path.join(folder, myfile), 'w') as fo:
        #            fo.write("type=" + emailbounce + "\n")
        #        send_unsubscribe_email2('admin@altcensored.com', emailbounce, myfile)
        #        db_unsubscribe_email(emailbounce)

        #        return (js["Type"])
        return (msg)
        #        return (msg["notificationType"])

        #        return (msg["notificationType"])
        #        return (msgjs)
        #        return (msgjs["mail"])
        #        return (msgjs["bounce"]["bouncedRecipients"][0])
        #        return (msgjs["bounce"]["bouncedRecipients"][0]["emailAddress"])  #WORKS
        return (emailcomplaint)  # WORKS


@bp.route('/test2')
@util.admin_login_required
def test2():
    now = datetime.datetime.now(timezone.utc)

    recipientscount = db_session.query(func.count(User.id)). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        scalar()

    users = db_session.query(User). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        limit(5).all()

    flash(recipientscount)
    for user in users:
        flash(user.email)
        time.sleep(1)

    return render_template('admin/admin_index.html')


def background(app, msg):
    app.logger.debug(msg)


def background2(app, msg):
    with app.app_context():
        app.logger.debug(msg)


@bp.route('/test3')
@util.admin_login_required
def test3():
    msg = 'yes'
    app = current_app._get_current_object()
    Thread(target=background, args=(app, msg)).start()
    return 'Hello, World!'


# works for single command (logger)


@bp.route('/test4')
@util.admin_login_required
def test4():
    msg = 'yes'
    app = current_app._get_current_object()
    Thread(target=background2, args=(app, msg)).start()
    return 'Hello, World!'


@bp.route('/test5')
@util.admin_login_required
def test5():
    recipientscount = db_session.query(func.count(User.id)). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        filter(User.settings['locale'].as_string() == "en"). \
        scalar()

    users = db_session.query(User). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        filter(User.settings['locale'].as_string() == "en"). \
        limit(5).all()

    flash(recipientscount)
    for user in users:
        flash(user.email)

    return render_template('admin/admin_index.html')


@bp.route('/test6')
@util.admin_login_required
def test6():
    commands = ["systemctl status allsync", "systemctl status find_archive", "ps -aef | grep -E 'channel|find|afs'", "df /dev/vda1"]
    ssh_command(commands)

    return render_template('admin/admin_messages.html')


@bp.route('/test500')
@util.admin_login_required
def test500():
    abort(500)