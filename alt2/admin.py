import os
import datetime
import requests
import json

from datetime import timezone
from flask_babelplus import lazy_gettext
from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for, current_app, jsonify)
from sqlalchemy import func
from .database import db_session
from .models import Mv_Channel, User, Entity, Source, Sources_to_Videos
from datatables import ColumnDT, DataTables
from . import util
from . import config

from .util import (
    confirm_token, send_all_mass_email, generate_confirmation_token
)
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'htm', 'html', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_unsubscribe_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('admin/admin_mass_email.html', confirm_url=confirm_url)
    send_mass_email(email, html)

def send_mass_email(email, subject, filename, service):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('newsletter/' + filename, confirm_url=confirm_url)
    send_all_mass_email(email, subject, html, service)

    user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    now = datetime.datetime.now(timezone.utc)
    user.email_lastsent_date = now
    db_session.add(user)
    db_session.commit()

def db_unsubscribe_email(email, action):
    user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
    now = datetime.datetime.now(timezone.utc)
    user.email_subscribed = False
    user.email_action = action
    user.updated = now
    db_session.add(user)
    db_session.commit()


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
        ColumnDT(func.to_char(Mv_Channel.ytc_publishedat,'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_deleteddate,'YYYY-mm-dd')),
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
        query = db_session.query().\
            select_from(Entity). \
            join(Sources_to_Videos). \
            join(Source).\
            filter(Source.ytc_id == ytc_id)

    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/mass_email', methods=['GET','POST'])
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

        sendlimit = 45
        global recipientscount
        service = (request.form['service'])
        email_status = (request.form['email_status'])
        subject = (request.form['subject'])

        if email_status == 'email_verified':
            usercount = db_session.query(func.count(User.id)). \
                filter(User.email_subscribed). \
                filter(User.email_verified). \
                scalar()
            users = db_session.query(User). \
                filter((User.email_lastsent_date) < func.current_date() - 28). \
                filter(User.email_subscribed). \
                filter(User.email_verified). \
                limit(sendlimit).all()

        if email_status == 'email_subscribed':
            usercount = db_session.query(func.count(User.id)). \
                filter(User.email_subscribed). \
                scalar()
            users = db_session.query(User). \
                filter((User.email_lastsent_date) < func.current_date() - 28). \
                filter(User.email_subscribed). \
                limit(sendlimit).all()

        if email_status == 'admin':
            usercount = '1'
            email = 'admin@altcensored.com'
            send_mass_email(email, subject, filename, service)
            flash(email)
            return redirect(url_for('admin.index'))

        flash(usercount)
        for user in users:
            send_mass_email(user.email, subject, filename, service)
            flash(user.email)

        return redirect(url_for('admin.index'))

    return render_template('admin/admin_mass_email.html', title = title)


@bp.route('/update_bounce', methods=['GET', 'POST'])
@util.admin_login_required
def update_bounce():
    jetlimit = 190
    title = "Upload and Process Bounce File"
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

    return render_template('admin/admin_mass_email.html', title = title)


@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def unsubscribe_email(token):
    email = confirm_token(token, None)
    l_msg = lazy_gettext('Unsubscribe ')
    item_quoted = (f'"{email}"')
    message = l_msg + ' ' + item_quoted + '?'

#        with open("test.txt", "w") as fo:
#            fo.write("This is Test Data line1\n")
#            fo.write("token=" + token + "\n")
#            fo.write("lastline")

    if email == False:
        conf = lazy_gettext('The unsubscribe link is invalid')
        flash(conf, 'error')
        return redirect(url_for('video.index'))
    else:
        user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
        if not user.email_subscribed:
            conf = item_quoted + lazy_gettext(' has already been unsubscribed')
            flash(conf, 'error')
            return redirect(url_for('video.index'))

    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(func.lower(User.email) == func.lower(email)).one()
            now = datetime.datetime.now(timezone.utc)
            user.email_subscribed = False
            user.updated = now
            db_session.add(user)
            db_session.commit()
            conf = item_quoted + lazy_gettext(' was unsubscribed')
            flash(conf, 'success')
            return redirect(url_for('video.index'))
        else:
            conf = item_quoted + lazy_gettext(' was NOT unsubscribed')
            flash(conf, 'error')
            return redirect(request.args.get('original_url', '/'))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/aws_bounce', methods = ['GET', 'POST', 'PUT'])
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

        emailbounce = msgjs["bounce"]["bouncedRecipients"][0]["emailAddress"]
        action = 'ab' #unenforced code for aws bounce
        db_unsubscribe_email(emailbounce, action)

    return 'OK\n'


@bp.route('/aws_complaint', methods = ['GET', 'POST'])
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

        emailcomplaint = msgjs["complaint"]["complainedRecipients"][0]["emailAddress"]
        action = 'ac' #unenforced code for aws complaint
        db_unsubscribe_email(emailcomplaint, action)

    return 'OK\n'


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
        return (emailcomplaint)  #WORKS

@bp.route('/test2')
@util.admin_login_required
def test2():
    now = datetime.datetime.now(timezone.utc)
    four_weeks_ago = now - datetime.timedelta(weeks=4)
#    flash(four_weeks_ago)

    users = db_session.query(User). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        limit(5).all()

    for user in users:
        flash(user.email)

    recipientscount = db_session.query(func.count(User.id)). \
        filter((User.email_lastsent_date) < func.current_date() - 28). \
        filter(User.email_verified). \
        filter(User.email_subscribed). \
        scalar()

    flash(recipientscount)

#    filter(User.email_verified).filter(User.email_subscribed). \

    return render_template('admin/admin_index.html')

