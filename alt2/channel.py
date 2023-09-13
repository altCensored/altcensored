from flask import (Blueprint, render_template, session, make_response, request, jsonify)
from werkzeug.exceptions import abort
from sqlalchemy import func
from .database import db_session
from .models import Mv_Video, Mv_Channel, User
from .pagination import Pagination
from datatables import ColumnDT, DataTables
from .util import (channels_latest, channels_deleted, channels_popular, channels_newest, channels_limited, channels_archived,
                   channeli, channeli_videocount, channeli_videos_newest, channeli_videos_popular,
                   get_channelcount, get_delchannelcount, get_archivechannelcount
                   )

bp = Blueprint('channel', __name__, url_prefix='/channel' )

PER_PAGE = 24
PER_PAGE_FEED = 100

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
#    channels = Mv_Channel.query.limit(PER_PAGE).offset(offset)
    channels = channels_latest(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_channelcount()
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/table')
def table():
    data = request.args.get('data', 'data_all')
    return render_template('channel/channel_table.html', data=data)


@bp.route('/data_all')
def data_all():
    columns = [
        ColumnDT(Mv_Channel.ytc_title),
        ColumnDT(Mv_Channel.ytc_id),
        ColumnDT(Mv_Channel.ytc_subscribercount),
        ColumnDT(Mv_Channel.ytc_viewcount),
        ColumnDT(Mv_Channel.total),
        ColumnDT(Mv_Channel.limited),
        ColumnDT(Mv_Channel.archive),
        ColumnDT(func.to_char(Mv_Channel.ytc_publishedat,'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_deleteddate,'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_addeddate, 'YYYY-mm-dd')),
    ]

    query = db_session.query().select_from(Mv_Channel)
    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/data_deleted')
def data_deleted():
    columns = [
        ColumnDT(Mv_Channel.ytc_title),
        ColumnDT(Mv_Channel.ytc_id),
        ColumnDT(Mv_Channel.ytc_subscribercount),
        ColumnDT(Mv_Channel.ytc_viewcount),
        ColumnDT(Mv_Channel.total),
        ColumnDT(Mv_Channel.limited),
        ColumnDT(Mv_Channel.archive),
        ColumnDT(func.to_char(Mv_Channel.ytc_publishedat,'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_deleteddate,'YYYY-mm-dd')),
        ColumnDT(func.to_char(Mv_Channel.ytc_addeddate, 'YYYY-mm-dd')),
    ]

    query = db_session.query().select_from(Mv_Channel).filter(Mv_Channel.ytc_deleted)
    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/new', defaults={'page': 1})
@bp.route('/new/page/<int:page>')
def new(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
#    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_publishedat.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = channels_newest(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_channelcount()
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
#    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_viewcount.desc()).limit(PER_PAGE).offset(offset)
    channels = channels_popular(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_channelcount()
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/deleted', defaults={'page': 1})
@bp.route('/deleted/page/<int:page>')
def deleted(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'deleted'
#    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
#    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
#    channels = Mv_Channel.query.filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = channels_deleted(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_delchannelcount()
    pagination = Pagination(page, PER_PAGE, session['delchannelcount'])
    return render_template('channel/channel_index.html', 
#        pagination=pagination, channels=channels, channelcount=channelcount, videocount=videocount, order=order)
        pagination = pagination, channels = channels, channelcount=session['delchannelcount'], order=order)

@bp.route('/deleted/feed', defaults={'page': 1})
@bp.route('/deleted/feed/page/<int:page>')
def deleted_feed(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'deleted'
#    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
#    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
#    channels = Mv_Channel.query.filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = channels_deleted(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_delchannelcount()
    pagination = Pagination(page, PER_PAGE_FEED, session['delchannelcount'])

    template = render_template('channel/channel_index.xml', pagination=pagination, channels=channels, channelcount=session['delchannelcount'], order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route('/limited', defaults={'page': 1})
@bp.route('/limited/page/<int:page>')
def limited(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'limited'
#    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
#    channels = Mv_Channel.query.order_by(Mv_Channel.limited.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    channels = channels_limited(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_channelcount()
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/archived', defaults={'page': 1})
@bp.route('/archived/page/<int:page>')
def archived(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'archived'
#    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
#    channels = Mv_Channel.query.filter(Mv_Channel.ytc_archive).limit(PER_PAGE).offset(offset)
    channels = channels_archived(PER_PAGE, offset)
    if not channels and page != 1:
        abort(404)
    get_archivechannelcount()
    pagination = Pagination(page, PER_PAGE, session['archivechannelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, channelcount=session['archivechannelcount'], order=order)


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    channels = Mv_Channel.query.limit(PER_PAGE_FEED).offset(offset)
    if not channels and page != 1:
        abort(404)
    get_channelcount()
    pagination = Pagination(page, PER_PAGE, session['channelcount'])

    template = render_template('channel/channel_index.xml', pagination=pagination, channels=channels, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route('/<ytc_id>', defaults={'page': 1})
@bp.route('/<ytc_id>/page/<int:page>')
def item(ytc_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    channel = channeli(ytc_id)
    if channel is None:
        abort(404)
    videocount = channeli_videocount(ytc_id)
    videos = channeli_videos_newest(ytc_id, PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater
    return render_template('channel/channel_item.html', pagination=pagination, channel=channel, videos=videos, videocount=videocount, order=order, watchlater=watchlater)


@bp.route('/<ytc_id>/popular', defaults={'page': 1})
@bp.route('/<ytc_id>/popular/page/<int:page>')
def item_popular(ytc_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    channel = channeli(ytc_id)
    if channel is None:
        abort(404)
    videocount = channeli_videocount(ytc_id)
    videos = channeli_videos_popular(ytc_id, PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater
    return render_template('channel/channel_item.html', pagination=pagination, channel=channel, videos=videos, videocount=videocount, order=order, watchlater=watchlater)


@bp.route('/<ytc_id>/feed', defaults={'page': 1})
@bp.route('/<ytc_id>/feed/page/<int:page>')
def item_feed(ytc_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(ytc_id=ytc_id).scalar()
    channel = Mv_Channel.query.get(ytc_id)
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc())
    videos = channeli_videos_newest(ytc_id, PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)

    template = render_template('channel/channel_item.xml', pagination=pagination, channel=channel, videos=videos, videocount=videocount, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response
