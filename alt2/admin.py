from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for, jsonify)
from sqlalchemy import func
from .database import db_session
from .models import Mv_Channel, User, Entity, Source, Sources_to_Videos
from datatables import ColumnDT, DataTables
from . import util
from .util import (
    send_welcome_email, generate_confirmation_token
)

bp = Blueprint('admin', __name__, url_prefix='/admin')

def send_confirm_email(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    html = render_template('auth/auth_activate.html', confirm_url=confirm_url)
    send_welcome_email(email, html)

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

@bp.route('/emails_send', methods=['GET', 'POST'])
@util.admin_login_required
def emails_send():
    if request.method == 'POST':
        email_status = (request.form['email_status'])
#        flash(email_status)

        if email_status == 'email_verified':
            recipientscount = db_session.query(func.count(User.id)).filter(User.email_verified).scalar()
#            recipients = User.query.filter(User.email_verified).all()
#            for recipient in recipients:
#                flash(recipient.email)

        if email_status == 'email_subscribed':
            recipientscount = db_session.query(func.count(User.id)).filter(User.email_subscribed).scalar()
            recipients = User.query.filter(User.email_subscribed).all()
            for recipient in recipients:
                flash(recipient.email)
                send_confirm_email(recipient.email)

        flash(recipientscount)
        return redirect(url_for('admin.index'))

    return render_template('admin/admin_emails_send.html')