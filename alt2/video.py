from flask import (
    Blueprint, render_template, request, make_response, session, current_app, flash)
from internetarchive import get_item
from sqlalchemy import func, text, case
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.exceptions import abort

from .database import db_session
from .models import Mv_Video, Mv_Channel, Mv_Category, Mv_Playlist, Mv_Altcen_user, User, Playlist
from .pagination import Pagination
import json
from .cache import cache

bp = Blueprint('video', __name__)

PER_PAGE = 24
CHANN_MAX_RESULT = 28

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
@cache.cached()
def index(page):
#    set_session()
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'latest'
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater
    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order, watchlater=watchlater)

@bp.route('/new', defaults={'page': 1})
@bp.route('/new/page/<int:page>')
@cache.cached()
def new(page):
#    set_session()
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'newest'
    videos = Mv_Video.query.order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater
    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order, watchlater=watchlater)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
@cache.cached()
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    videos = Mv_Video.query.order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater
    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order, watchlater=watchlater)


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'latest'
    videos = Mv_Video.query.order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    template = render_template('video/video_index.xml', pagination=pagination, videos=videos, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route("/watch")
def watch():
#    set_session()
    video_id = request.args.get('v', None)
    playlist = request.args.get('playlist', None)
    userlist = request.args.get('userlist', None)

    if video_id is None:
        abort(404)
    video = Mv_Video.query.get(video_id)
    if video is None:
        abort(404)

    cat_name = video.category
    tagstring = video.tags
    session['first_vid_pub'] = video.published
    session.modified = True

    try:
        tags = tagstring.split(",")
    except:
        tags = None

    try:
        category = Mv_Category.query.filter_by(cat_name=cat_name).first()
        cat_id = category.cat_id
    except:
        cat_id = 25
    channel = Mv_Channel.query.get(video.ytc_id)

    if playlist:
        playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
        if playlist is None:
            abort(404)
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(playlist.videos))))},
            value=Mv_Video.extractor_data
        )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(playlist.videos)).order_by(ordering)

    elif userlist == "history":
        user = User.query.filter(User.id == session['user']['id']).scalar()
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watched))))},
            value=Mv_Video.extractor_data
        )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watched)).order_by(ordering)

    elif userlist == "watchlater":
        user = User.query.filter(User.id == session['user']['id']).scalar()
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watchlater))))},
            value=Mv_Video.extractor_data
        )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watchlater)).order_by(ordering)

    else:
        videos = db_session.query(Mv_Video).filter(Mv_Video.ytc_id == video.ytc_id,
                                                   Mv_Video.published <= video.published,
                                                   Mv_Video.extractor_data != video_id) \
            .order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE)

    try:
        item = get_item('youtube-' + video_id)
        fileitem = next(item for item in item.files if item["format"] == "JSON")
        filenamelong = (fileitem['name'])
        filename = filenamelong[:-10]
        IARCHIVEURL = current_app.config['IARCHIVEURL']
        video_url = IARCHIVEURL + video_id + "/" + filename
        video_url_short = IARCHIVEURL + video_id + "/"
#        if "access-restricted-item" in item.metadata: raise Exception
#        if "altcen_hosted" in item.metadata: raise Exception
    except:
        MYSERVER_URL = current_app.config['MYSERVER_URL']
        video_url = MYSERVER_URL + "/videos/" + video_id
        IARCHIVEURL = current_app.config['IARCHIVEURL']
        video_url_short = IARCHIVEURL + video_id + "/"

    playlist_titles = []
    not_in_watchlater = None

    if session.get('user') is not None:
        user = db_session.query(User).filter(User.email == session['user']['email']).one()

        try:
            user.watched += [video.extractor_data]
        except:
            user.watched = [video.extractor_data]

        user.watched = list(dict.fromkeys(user.watched))
        flag_modified(user, "watched")
        db_session.commit()

        if user.watchlater and (video_id not in user.watchlater):
            not_in_watchlater = True

        plists = db_session.query(Playlist).filter(Playlist.user_id == user.id)

        for plist in plists:
            if video_id not in plist.videos:
                playlist_titles.append(plist.title)

    return render_template('video/video_item.html', video_url=video_url, video_url_short=video_url_short,
                           video_id=video_id, channel=channel, video=video, videos=videos, cat_id=cat_id, tags=tags,
                           playlist=playlist, userlist=userlist, not_in_watchlater=not_in_watchlater,
                           playlist_titles=playlist_titles)


@bp.route('/embed/<video_id>')
def embed(video_id):
    video = Mv_Video.query.get(video_id)
    if video is None:
        abort(404)

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
        if playlist is None:
            abort(404)
        if len(playlist.videos) > 1:
            idx = (playlist.videos).index(video.extractor_data)
            next_video = (playlist.videos).pop(idx - 1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    elif userlist == "history":
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if len(user.watched) > 1:
            idx = (user.watched).index(video.extractor_data)
            next_video = (user.watched).pop(idx - 1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    elif userlist == "watchlater":
        user = User.query.filter(User.id == session['user']['id']).scalar()
        print("Watch Later", user.watchlater)
        if len(user.watchlater) > 1:
            idx = (user.watchlater).index(video.extractor_data)
            next_video = (user.watchlater).pop(idx - 1)
            if not session.get('looplist') and idx == 0:
                next_video = None

    else:
        try:
            videos = db_session.query(Mv_Video.extractor_data).filter(Mv_Video.ytc_id == video.ytc_id,
                                                                  Mv_Video.published <= session['first_vid_pub']) \
            .order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE)
        except:
            videos = db_session.query(Mv_Video.extractor_data).filter(Mv_Video.ytc_id == video.ytc_id) \
            .order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc()).limit(PER_PAGE)

        if videos.count() > 1:
            videos_extractor_list = [r[0] for r in videos]
            videos_extractor_list.reverse()

            try:
                idx = (videos_extractor_list).index(video.extractor_data)
            except:
                idx = len(videos_extractor_list)
#            listlen = len(videos_extractor_list)
            next_video = (videos_extractor_list).pop(idx - 1)
            try:
                videos_extractor_list.remove(video_id)
            except:
                pass
            if not session.get('looplist') and idx == 0:
                next_video = None

    return render_template('video/video_embed.html', video_url=video_url, next_video=next_video, playlist=playlist,
                           userlist=userlist)

@bp.route("/search", defaults={'page': 1})
@bp.route('/search/page/<int:page>')
def search(page):
#    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'default'
    playlist_ident = request.args.get('playlist', None)

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
        params(search=search).all()

    my_to_tsquery_playlist = text("Mv_Playlist.document @@ to_tsquery(:search)")
    my_ts_rank_playlist = text("ts_rank(Mv_Playlist.document, to_tsquery(:search)) DESC")
    searchplaylists = db_session.query(Mv_Playlist).\
        filter(my_to_tsquery_playlist).\
        order_by(my_ts_rank_playlist).\
        params(search=search).all()

    my_to_tsquery_altcen_user = text("Mv_Altcen_user.document @@ to_tsquery(:search)")
    my_ts_rank_altcen_user = text("ts_rank(Mv_Altcen_user.document, to_tsquery(:search)) DESC")
    altcen_users = db_session.query(Mv_Altcen_user).\
        filter(my_to_tsquery_altcen_user).\
        order_by(my_ts_rank_altcen_user).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    searchplaylistcount = db_session.query(func.count(Mv_Playlist.id)).filter(my_to_tsquery_playlist).params(search=search).scalar()
    usercount = db_session.query(func.count(Mv_Altcen_user.id)).filter(my_to_tsquery_altcen_user).params(search=search).scalar()

    pagination = Pagination(page, PER_PAGE, videocount)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    playlist = None
    if playlist_ident:
        channels = None
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    if not videos and page != 1:
        abort(404)
    return render_template('video/video_search.html', videos=videos, pagination=pagination, usercount=usercount,\
                           channcount=channcount, searchplaylistcount=searchplaylistcount, rawsearch=rawsearch,\
                           searchplaylists=searchplaylists, altcen_users=altcen_users,\
                           order=order, channels=channels, videocount=videocount, watchlater=watchlater, playlist=playlist)


@bp.route("/search/latest", defaults={'page': 1})
@bp.route('/search/latest/page/<int:page>')
def search_latest(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'latest'
    playlist_ident = request.args.get('playlist', None)

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
        order_by(my_ts_rank_channel).\
        params(search=search).all()

    my_to_tsquery_playlist = text("Mv_Playlist.document @@ to_tsquery(:search)")
    my_ts_rank_playlist = text("ts_rank(Mv_Playlist.document, to_tsquery(:search)) DESC")
    searchplaylists = db_session.query(Mv_Playlist).\
        filter(my_to_tsquery_playlist).\
        order_by(my_ts_rank_playlist).\
        params(search=search).all()

    my_to_tsquery_altcen_user = text("Mv_Altcen_user.document @@ to_tsquery(:search)")
    my_ts_rank_altcen_user = text("ts_rank(Mv_Altcen_user.document, to_tsquery(:search)) DESC")
    altcen_users = db_session.query(Mv_Altcen_user).\
        filter(my_to_tsquery_altcen_user).\
        order_by(my_ts_rank_altcen_user).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    searchplaylistcount = db_session.query(func.count(Mv_Playlist.id)).filter(my_to_tsquery_playlist).params(search=search).scalar()
    usercount = db_session.query(func.count(Mv_Altcen_user.id)).filter(my_to_tsquery_altcen_user).params(search=search).scalar()

    pagination = Pagination(page, PER_PAGE, videocount)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    playlist = None
    if playlist_ident:
        channels = None
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    if not videos and page != 1:
        abort(404)
    return render_template('video/video_search.html', videos=videos, pagination=pagination, usercount=usercount,\
                           channcount=channcount, searchplaylistcount=searchplaylistcount, rawsearch=rawsearch,\
                           searchplaylists=searchplaylists, altcen_users=altcen_users,\
                           order=order, channels=channels, videocount=videocount, watchlater=watchlater, playlist=playlist)


@bp.route("/search/new", defaults={'page': 1})
@bp.route('/search/new/page/<int:page>')
def search_new(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    order = 'newest'
    playlist_ident = request.args.get('playlist', None)

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
        order_by(my_ts_rank_channel).\
        params(search=search).all()

    my_to_tsquery_playlist = text("Mv_Playlist.document @@ to_tsquery(:search)")
    my_ts_rank_playlist = text("ts_rank(Mv_Playlist.document, to_tsquery(:search)) DESC")
    searchplaylists = db_session.query(Mv_Playlist).\
        filter(my_to_tsquery_playlist).\
        order_by(my_ts_rank_playlist).\
        params(search=search).all()

    my_to_tsquery_altcen_user = text("Mv_Altcen_user.document @@ to_tsquery(:search)")
    my_ts_rank_altcen_user = text("ts_rank(Mv_Altcen_user.document, to_tsquery(:search)) DESC")
    altcen_users = db_session.query(Mv_Altcen_user).\
        filter(my_to_tsquery_altcen_user).\
        order_by(my_ts_rank_altcen_user).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    searchplaylistcount = db_session.query(func.count(Mv_Playlist.id)).filter(my_to_tsquery_playlist).params(search=search).scalar()
    usercount = db_session.query(func.count(Mv_Altcen_user.id)).filter(my_to_tsquery_altcen_user).params(search=search).scalar()

    pagination = Pagination(page, PER_PAGE, videocount)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    playlist = None
    if playlist_ident:
        channels = None
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    if not videos and page != 1:
        abort(404)
    return render_template('video/video_search.html', videos=videos, pagination=pagination, usercount=usercount,\
                           channcount=channcount, searchplaylistcount=searchplaylistcount, rawsearch=rawsearch,\
                           searchplaylists=searchplaylists, altcen_users=altcen_users,\
                           order=order, channels=channels, videocount=videocount, watchlater=watchlater, playlist=playlist)


@bp.route("/search/popular", defaults={'page': 1})
@bp.route('/search/popular/page/<int:page>')
def search_popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    rawsearch1 = request.args.get('q', None)
    rawsearch = rawsearch1.strip()
    search = rawsearch.replace(" " , "&")
    playlist_ident = request.args.get('playlist', None)

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
        order_by(my_ts_rank_channel).\
        params(search=search).all()

    my_to_tsquery_playlist = text("Mv_Playlist.document @@ to_tsquery(:search)")
    my_ts_rank_playlist = text("ts_rank(Mv_Playlist.document, to_tsquery(:search)) DESC")
    searchplaylists = db_session.query(Mv_Playlist).\
        filter(my_to_tsquery_playlist).\
        order_by(my_ts_rank_playlist).\
        params(search=search).all()

    my_to_tsquery_altcen_user = text("Mv_Altcen_user.document @@ to_tsquery(:search)")
    my_ts_rank_altcen_user = text("ts_rank(Mv_Altcen_user.document, to_tsquery(:search)) DESC")
    altcen_users = db_session.query(Mv_Altcen_user).\
        filter(my_to_tsquery_altcen_user).\
        order_by(my_ts_rank_altcen_user).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    searchplaylistcount = db_session.query(func.count(Mv_Playlist.id)).filter(my_to_tsquery_playlist).params(search=search).scalar()
    usercount = db_session.query(func.count(Mv_Altcen_user.id)).filter(my_to_tsquery_altcen_user).params(search=search).scalar()

    pagination = Pagination(page, PER_PAGE, videocount)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    playlist = None
    if playlist_ident:
        channels = None
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    if not videos and page != 1:
        abort(404)
    return render_template('video/video_search.html', videos=videos, pagination=pagination, usercount=usercount,\
                           channcount=channcount, searchplaylistcount=searchplaylistcount, rawsearch=rawsearch,\
                           searchplaylists=searchplaylists, altcen_users=altcen_users,\
                           order=order, channels=channels, videocount=videocount, watchlater=watchlater, playlist=playlist)


@bp.route('/play-next', methods=['GET', 'POST'])
def play_next():
    if request.method == 'POST':
        data = json.loads(request.data)
#        session['playnext'] = data['checked']
        session['playnext'] = not session['playnext']
        return json.dumps({'playnext': session['playnext']})
    else:
        return json.dumps({'playnext': session['playnext']})
