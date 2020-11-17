from flask import (
    Blueprint, render_template, request, jsonify)
from sqlalchemy import func
from .database import db_session
from .models import Mv_Video, Mv_Channel, User
from datatables import ColumnDT, DataTables
from . import util

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/table')
@util.admin_login_required
def table():
    data = request.args.get('data', 'data_all')
    return render_template('channel/channel_table_admin.html', data=data)


@bp.route('/data_all')
@util.admin_login_required
def data_all():
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