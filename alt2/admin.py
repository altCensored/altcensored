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
    confirm_token, send_mass_email, generate_confirmation_token
)
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'htm', 'html'}

def msg_process(msg, tstamp):
    js = json.loads(msg)
    msg = 'Region: {0} / Alarm: {1}'.format(
        js['Region'], js['AlarmName']
    )
    # do stuff here, like calling your favorite SMS gateway API

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_unsubscribe_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('admin/admin_mass_email.html', confirm_url=confirm_url)
    send_mass_email(email, html)

def send_unsubscribe_email2(email, subject, htmlfile):
    token = generate_confirmation_token(email)
    confirm_url = url_for('admin.unsubscribe_email', token=token, _external=True)
    html = render_template('newsletter/' + htmlfile, confirm_url=confirm_url)
    send_mass_email(email, subject, html)

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


@bp.route('/upload_email', methods=['GET', 'POST'])
@util.admin_login_required
def upload_email():
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
            flash(folder_file + ' was uploaded')
            return redirect(url_for('admin.index'))
    return render_template('admin/admin_upload_email.html')

@bp.route('/send_email', methods=['GET','POST'])
@util.admin_login_required
def send_email():
    global recipientscount
    if request.method == 'POST':
        email_status = (request.form['email_status'])
        subject = (request.form['subject'])
        htmlfile = (request.form['filename'])
#        flash(email_status)
#        flash(htmlfile)

        if email_status == 'email_verified':
            recipientscount = db_session.query(func.count(User.id)).filter(User.email_verified).scalar()
            recipients = User.query.filter(User.email_verified).all()
            for recipient in recipients:
                flash(recipient.email)

        if email_status == 'email_subscribed':
            recipientscount = db_session.query(func.count(User.id)).filter(User.email_subscribed).scalar()
            recipients = User.query.filter(User.email_subscribed).all()
            for recipient in recipients:
                flash(recipient.email)
                send_unsubscribe_email(recipient.email)

        if email_status == 'admin':
            recipientscount = '1'
            flash('email sent to admin@altcensored.com')
            send_unsubscribe_email2('admin@altcensored.com', subject, htmlfile)

        flash(recipientscount)
        return redirect(url_for('admin.index'))

    return render_template('admin/admin_send_email.html')


@bp.route('/confirm/<token>', methods=['GET', 'POST'])
def unsubscribe_email(token):
    email = confirm_token(token, None)
    l_msg = lazy_gettext('Unsubscribe ')
    item_quoted = (f'"{email}"')
    message = l_msg + ' ' + item_quoted + '?'

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


@bp.route('/aws_bounce1/<token>', methods=['GET', 'POST'])
def aws_bounce1(token):
    send_unsubscribe_email2('admin@altcensored.com', token, 'altcen3.html')
    return redirect(url_for('video.index'))

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
        msg_process(js['Message'], js['Timestamp'])

    return 'OK\n'

@bp.route('/aws_complaint', methods = ['GET', 'POST', 'PUT'])
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
        msg_process(js['Message'], js['Timestamp'])

    return 'OK\n'