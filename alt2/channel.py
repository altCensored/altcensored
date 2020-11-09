from flask import (Blueprint, render_template, session, make_response, request, jsonify)
from werkzeug.exceptions import abort
from sqlalchemy import func
from .database import db_session
from .models import Mv_Video, Mv_Channel, User
from .pagination import Pagination
from .util import set_session
from datatables import ColumnDT, DataTables

bp = Blueprint('channel', __name__, url_prefix='/channel' )

PER_PAGE = 24
PER_PAGE_FEED = 100

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    channels = Mv_Channel.query.limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/table')
def table():
    return render_template('channel/channel_table.html')

@bp.route('/data')
def data():
    columns = [
        ColumnDT(Mv_Channel.ytc_title),
        ColumnDT(Mv_Channel.total),
        ColumnDT(Mv_Channel.limited),
        ColumnDT(Mv_Channel.ytc_publishedat),
        ColumnDT(Mv_Channel.ytc_deleteddate),
    ]

    query = db_session.query().select_from(Mv_Channel)
    params = request.args.to_dict()
    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())


@bp.route('/new', defaults={'page': 1})
@bp.route('/new/page/<int:page>')
def new(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_publishedat.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    channels = Mv_Channel.query.order_by(Mv_Channel.ytc_viewcount.desc()).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, order=order)


@bp.route('/deleted', defaults={'page': 1})
@bp.route('/deleted/page/<int:page>')
def deleted(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'deleted'
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    channels = Mv_Channel.query.filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['delchannelcount'])
    return render_template('channel/channel_index.html', 
        pagination=pagination, channels=channels, channelcount=channelcount, videocount=videocount, order=order)


@bp.route('/deleted/feed', defaults={'page': 1})
@bp.route('/deleted/feed/page/<int:page>')
def deleted_feed(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'deleted'
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    channels = Mv_Channel.query.filter(Mv_Channel.ytc_deleted).order_by(Mv_Channel.ytc_deleteddate.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE_FEED, session['channelcount'])

    template = render_template('channel/channel_index.xml', pagination=pagination, channels=channels, channelcount=channelcount, videocount=videocount, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route('/limited', defaults={'page': 1})
@bp.route('/limited/page/<int:page>')
def limited(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'limited'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    channels = Mv_Channel.query.order_by(Mv_Channel.limited.desc(),Mv_Channel.ytc_id.desc()).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, videocount=videocount, order=order)


@bp.route('/archived', defaults={'page': 1})
@bp.route('/archived/page/<int:page>')
def archived(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'archived'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    channels = Mv_Channel.query.filter(Mv_Channel.ytc_archive).limit(PER_PAGE).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])
    return render_template('channel/channel_index.html', pagination=pagination, channels=channels, videocount=videocount, order=order)


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    channels = Mv_Channel.query.limit(PER_PAGE_FEED).offset(offset)
    if not channels and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['channelcount'])

    template = render_template('channel/channel_index.xml', pagination=pagination, channels=channels, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route('/<ytc_id>', defaults={'page': 1})
@bp.route('/<ytc_id>/page/<int:page>')
def item(ytc_id,page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(ytc_id=ytc_id).scalar()
    channel = Mv_Channel.query.get(ytc_id)
    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc(),Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset)
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
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(ytc_id=ytc_id).scalar()
    channel = Mv_Channel.query.get(ytc_id)
    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
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
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(ytc_id=ytc_id).scalar()
    channel = Mv_Channel.query.get(ytc_id)
    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc())
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)

    template = render_template('channel/channel_item.xml', pagination=pagination, channel=channel, videos=videos, videocount=videocount, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response
