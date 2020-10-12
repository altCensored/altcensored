from flask import (
    Blueprint, render_template, request, make_response, session, current_app)
from internetarchive import get_item
from sqlalchemy import func, text, case
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.exceptions import abort

from .database import db_session
from .models import Mv_Video, Mv_Channel, Mv_Category, User, Playlist
from .pagination import Pagination
from .util import set_session

bp = Blueprint('video', __name__ )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.email == session['user']['email']).scalar()
        if user.watchlater:
            watchlater=user.watchlater

    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order, watchlater=watchlater, \
     videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount )


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    videocount = db_session.query(func.count(Mv_Video.id)).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    template = render_template('video/video_index.xml', pagination=pagination, videos=videos, \
        videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)
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
    return render_template('video/video_index.html', pagination=pagination, videos=videos, \
        videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)


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
    return render_template('video/video_index.html', pagination=pagination, videos=videos, \
        videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)


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
    return render_template('video/video_index.html', pagination=pagination, videos=videos, \
        videocount=videocount, channelcount=channelcount, delchannelcount=delchannelcount, order=order)

 
@bp.route("/watch")
def watch():
    video_id = request.args.get('v', None)
    playlist = request.args.get('playlist', None)
    userlist = request.args.get('userlist', None)
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

    if playlist:
        playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(playlist.videos))))},
            value=Mv_Video.extractor_data
         )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(playlist.videos)).order_by(ordering)

    elif userlist == "history":
        user = User.query.filter(User.email == session['user']['email']).scalar()
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watched))))},
            value=Mv_Video.extractor_data
         )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watched)).order_by(ordering)

    elif userlist == "watchlater":
        user = User.query.filter(User.email == session['user']['email']).scalar()
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watchlater))))},
            value=Mv_Video.extractor_data
         )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watchlater)).order_by(ordering)

    else:
        videos = Mv_Video.query.filter_by(ytc_id=ytc_id).order_by(Mv_Video.published.desc(),\
            Mv_Video.extractor_data.desc()).limit(PER_PAGE)
        playlist = None

    try:
        item = get_item('youtube-' + video_id)
        fileitem = next(item for item in item.files if item["format"] == "JSON")
        filenamelong = (fileitem['name'])
        filename = filenamelong[:-10]
        IARCHIVEURL = current_app.config['IARCHIVEURL']
        video_url = IARCHIVEURL + video_id + "/" + filename
        video_url_short = IARCHIVEURL + video_id + "/"
        if "access-restricted-item" in item.metadata: raise Exception
        if "altcen_hosted" in item.metadata: raise Exception
    except:
        MYSERVER_URL = current_app.config['MYSERVER_URL']
        video_url = MYSERVER_URL + "/videos/" + video_id

    if session.get('user') is not None:
        user = db_session.query(User).filter(User.email == session['user']['email']).one()

        try:
            user.watched += [video.extractor_data]
        except:
            user.watched = [video.extractor_data]

        user.watched = list(dict.fromkeys(user.watched))
        flag_modified(user, "watched")
        db_session.commit()

    return render_template('video/video_item.html', video_url=video_url, video_url_short=video_url_short,\
     video_id=video_id, channel=channel, video=video, videos=videos, cat_id=cat_id, tags=tags,\
     playlist=playlist, userlist=userlist)

@bp.route('/embed/<video_id>')
def embed(video_id):
    video = Mv_Video.query.get(video_id)
    playlist = request.args.get('playlist', None)
    userlist = request.args.get('userlist', None)

    try:
        item = get_item('youtube-' + video_id)
        fileitem = next(item for item in item.files if item["format"] == "JSON")
        filenamelong = (fileitem['name'])
        filename = filenamelong[:-10]
        IARCHIVEURL = current_app.config['IARCHIVEURL']
        video_url = IARCHIVEURL + video_id + "/" + filename
        if "access-restricted-item" in item.metadata: raise Exception
        if "altcen_hosted" in item.metadata: raise Exception
    except:
        MYSERVER_URL = current_app.config['MYSERVER_URL']
        video_url = MYSERVER_URL + "/videos/" + video_id

    next_video = None

    if playlist:
        playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
        if len(playlist.videos) > 1:
            idx = (playlist.videos).index(video.extractor_data)
            next_video = (playlist.videos).pop(idx-1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    elif userlist == "history":
        user = User.query.filter(User.email == session['user']['email']).scalar()
        if len(user.watched) > 1:
            idx = (user.watched).index(video.extractor_data)
            next_video = (user.watched).pop(idx-1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    elif userlist == "watchlater":
        user = User.query.filter(User.email == session['user']['email']).scalar()
        print("Watch Later", user.watchlater)
        if len(user.watchlater) > 1:
            idx = (user.watchlater).index(video.extractor_data)
            next_video = (user.watchlater).pop(idx-1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    else:
        videos = db_session.query(Mv_Video.extractor_data).filter_by(ytc_id=video.ytc_id).order_by(Mv_Video.published.asc()).limit(PER_PAGE)
        if videos.count() > 1:
            videos_extractor = [r[0] for r in videos]
            videos_extractor_list = list(videos_extractor)
            try:
                idx = (videos_extractor_list).index(video.extractor_data)
                listlen = len(videos_extractor_list)
                next_video = (videos_extractor_list).pop(idx-1)
                if not session.get('looplist') and idx == 0:
                    next_video = None
            except:
                next_video = None

    return render_template('video/video_embed.html', video_url=video_url, next_video=next_video, playlist=playlist, userlist=userlist)


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
        return render_template('video/video_search.html', videos=videos, pagination=pagination, \
            rawsearch=rawsearch,  order=order, delchannelcount=delchannelcount, channels=channels, videocount=videocount)


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
        return render_template('video/video_search.html', videos=videos, pagination=pagination, \
            rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


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
        return render_template('video/video_search.html', videos=videos, pagination=pagination, \
            rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


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
        return render_template('video/video_search.html', videos=videos, pagination=pagination, \
            rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)


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
        return render_template('video/video_search.html', videos=videos, pagination=pagination, \
            rawsearch=rawsearch,  order=order, channels=channels, videocount=videocount)
