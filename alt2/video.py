from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    send_from_directory, make_response )
from werkzeug.exceptions import abort
from sqlalchemy import func, text
from internetarchive import get_item
from .database import db_session
from .models import Mv_Video, Mv_Channel, Mv_Category
from .pagination import Pagination

bp = Blueprint('video', __name__ )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
#    videos = Mv_Video.query.limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('video/video_index.html', pagination=pagination, videos=videos, videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
#    videos = Mv_Video.query.limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)

    template = render_template('video/video_index.xml', pagination=pagination, videos=videos, videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response    


@bp.route('/new', defaults={'page': 1})
@bp.route('/new/page/<int:page>')
def new(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.published.desc(),Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('video/video_index.html', pagination=pagination, videos=videos, videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)


@bp.route('/old', defaults={'page': 1})
@bp.route('/old/page/<int:page>')
def old(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'oldest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.published.asc(),Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('video/video_index.html', pagination=pagination, videos=videos, videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'    
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('video/video_index.html', pagination=pagination, videos=videos, videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)
 
 
@bp.route("/watch")
def watch():
    video_id = request.args.get('v', None)
    video = Mv_Video.query.get(video_id)
    cat_name = video.category
    tagstring = video.tags

    try:       
        tags = tagstring.split(",")
    except:
        tags = None

    category = Mv_Category.query.filter_by(cat_name=cat_name).first()

    cat_id = category.cat_id

    ytc_id = video.ytc_id
    channel = Mv_Channel.query.get(ytc_id)
    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).limit(PER_PAGE)
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).all()
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc()).limit(12).all()

    try:
        item = get_item('youtube-' + video_id)
        fileitem = next(item for item in item.files if item["format"] == "JSON")
#        fileitem = next(item for item in item.files)
        filenamelong = (fileitem['name'])
        filename = filenamelong[:-10]
        ia_url = "https://archive.org/download/youtube-" + video_id + "/" + filename
        ia_url_short = "https://archive.org/download/youtube-" + video_id + "/"
#        ia_url = "https://archive.org/embed/youtube-" + video_id + "/" + filename
    except:
        ia_url =  None

    return render_template('video/video_item.html', ia_url=ia_url, ia_url_short= ia_url_short,\
        video_id=video_id, channel=channel, video=video, videos=videos, cat_id=cat_id, tags=tags)

@bp.route('/embed/<video_id>')
def embed(video_id):
#    video_id = request.args.get('v', None)
    video = Mv_Video.query.get(video_id)


#    ytc_id = video.ytc_id
#    channel = Mv_Channel.query.get(ytc_id)
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).all()
#    videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc()).limit(12).all()

    try:
        item = get_item('youtube-' + video_id)
        fileitem = next(item for item in item.files if item["format"] == "JSON")
        filenamelong = (fileitem['name'])
        filename = filenamelong[:-10]
        ia_url = "https://archive.org/download/youtube-" + video_id + "/" + filename
#        ia_url = "https://archive.org/embed/youtube-" + video_id + "/" + filename
    except:
        ia_url =  None

    return render_template('video/video_embed.html', ia_url=ia_url, video_id=video_id, video=video)


@bp.route("/search", defaults={'page': 1})
@bp.route('/search/page/<int:page>')
def search(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'default'

    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(my_ts_rank_video).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        order_by(my_ts_rank_channel).\
        limit(24).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleteddate!='2001-01-01').scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('video/video_index.html', videos=videos) 
    else:
        return render_template('video/video_search.html', videos=videos, pagination=pagination, rawsearch=rawsearch,  order=order, delchannelcount=delchannelcount, channels=channels, videocount=videocount)


@bp.route("/search/latest", defaults={'page': 1})
@bp.route('/search/latest/page/<int:page>')
def search_latest(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'latest'

    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.id.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        limit(24).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('video/video_index.html', videos=videos) 
    else:
        return render_template('video/video_search.html', videos=videos, pagination=pagination, rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


@bp.route("/search/new", defaults={'page': 1})
@bp.route('/search/new/page/<int:page>')
def search_new(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'newest'

    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.published.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        limit(24).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('video/video_index.html', videos=videos) 
    else:
        return render_template('video/video_search.html', videos=videos, pagination=pagination, rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


@bp.route("/search/old", defaults={'page': 1})
@bp.route('/search/old/page/<int:page>')
def search_old(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'oldest'

    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.published.asc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        limit(24).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('video/video_index.html', videos=videos) 
    else:
        return render_template('video/video_search.html', videos=videos, pagination=pagination, rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


@bp.route("/search/popular", defaults={'page': 1})
@bp.route('/search/popular/page/<int:page>')
def search_popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")

    order = 'popular'
    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.yt_views.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        limit(24).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('video/video_index.html', videos=videos) 
    else:
        return render_template('video/video_search.html', videos=videos, pagination=pagination, rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)
