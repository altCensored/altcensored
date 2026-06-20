import logging
import os
import json
from flask import (
    Blueprint, render_template, request, make_response, session, current_app, abort, flash, jsonify)
from markupsafe import Markup
from sqlalchemy import func, text, case, select
from sqlalchemy.orm.attributes import flag_modified
from threading import Thread
from .database import db_session
from .models import MvVideo, MvChannel, MvCategory, MvPlaylist, MvAltcenUser, User, Playlist
from .pagination import Pagination
from datetime import datetime, timezone
from .util import (videos_newest, videos_popular, videos_latest, get_videocount, get_playnext,
                   videos_trending, get_ia_item, increment_video_counter, check_ac_object_exists,
                   get_current_user)
from . import config

logger = logging.getLogger(__name__)

bp = Blueprint('video', __name__)
FLASH_MSG = config.FLASH_MSG

PER_PAGE = 24
CHANN_MAX_RESULT = 28


def _resolve_video_url(video: MvVideo, video_id: str) -> str:
    IARCHIVEURL = current_app.config['IARCHIVEURL']
    VIDEOSERVER_URL = current_app.config['VIDEOSERVER_URL']
    unavailable_url = f'{VIDEOSERVER_URL}unavailable/unavailable'

    # Only hit S3 when exists_ac is truthy — None and False both skip the round-trip.
    # The scraper sets exists_ac=True on upload, so None reliably means "never in S3".
    if video.exists_ac:
        try:
            s3_exists = check_ac_object_exists(video_id)
        except Exception:
            s3_exists = False
        if s3_exists:
            return VIDEOSERVER_URL + video_id + "/" + video_id

    if video.dark_ia or video.restricted_ia or video.loggedin_ia or video.novideo_ia:
        return unavailable_url

    if video.videofile:
        root, _ext = os.path.splitext(video.videofile)
        return IARCHIVEURL + video_id + "/" + root

    if (
        video.thumbnail
        and 'maxresdefault' not in video.thumbnail
        and not video.thumbnail.startswith('http')
    ):
        root, _ext = os.path.splitext(video.thumbnail)
        return IARCHIVEURL + video_id + "/" + root

    # is False (identity) — None means unknown, must still try get_ia_item().
    if video.exists_ia is False:
        return unavailable_url

    return get_ia_item(video.extractor_data)


@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'newest'
    videos = videos_newest(PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    session['videocount'] = get_videocount()
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = get_current_user().watchlater if get_current_user() else None
    if FLASH_MSG is not None:
        flash(Markup(FLASH_MSG), 'error')

    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order,
                           watchlater=watchlater)


@bp.route('/new', defaults={'page': 1})
@bp.route('/new/page/<int:page>')
def new(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'trending'
    videos = videos_trending(PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    get_videocount()
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = get_current_user().watchlater if get_current_user() else None
    if FLASH_MSG is not None:
        flash(Markup(FLASH_MSG), 'error')

    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order,
                           watchlater=watchlater)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'popular'
    videos = videos_popular(PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    get_videocount()
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = get_current_user().watchlater if get_current_user() else None
    if FLASH_MSG is not None:
        flash(Markup(FLASH_MSG), 'error')

    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order,
                           watchlater=watchlater)


@bp.route('/latest', defaults={'page': 1})
@bp.route('/latest/page/<int:page>')
def latest(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'latest'
    videos = videos_latest(PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    get_videocount()
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    watchlater = get_current_user().watchlater if get_current_user() else None
    if FLASH_MSG is not None:
        flash(Markup(FLASH_MSG), 'error')

    return render_template('video/video_index.html', pagination=pagination, videos=videos, order=order,
                           watchlater=watchlater)


@bp.route('/feed', defaults={'page': 1})
@bp.route('/feed/page/<int:page>')
def feed(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'latest'
    videos = videos_newest(PER_PAGE, offset)
    if not videos and page != 1:
        abort(404)
    get_videocount()
    pagination = Pagination(page, PER_PAGE, session['videocount'])
    template = render_template('video/video_index.xml', pagination=pagination, videos=videos, order=order)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


@bp.route("/watch")
def watch():
    video_id = request.args.get('v', None)
    playlist = request.args.get('playlist', None)
    userlist: str | None = request.args.get('userlist', None)

    NEW_FLASH_MSG = None

    if video_id is None:
        abort(404)
    video = db_session.execute(select(MvVideo).filter(MvVideo.extractor_data == video_id)).scalar()
    if video is None:
        abort(404)

    cat_name = video.category
    tagstring = video.tags
    session['first_vid_pub'] = video.published
    session.modified = True

    try:
        tags = tagstring.split(",")
    except Exception:
        tags = None

    try:
        category = MvCategory.query.filter_by(cat_name=cat_name).first()
        cat_id = category.cat_id
    except Exception:
        cat_id = 25
    channel = db_session.execute(select(MvChannel).filter(MvChannel.ytc_id == video.ytc_id)).scalar()

    if playlist:
        playlist = db_session.execute(select(Playlist).filter(Playlist.hashid == playlist)).scalar()
        if playlist is None:
            abort(404)
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(playlist.videos))))},
            value=MvVideo.extractor_data
        )
        videos = MvVideo.query.filter(MvVideo.extractor_data.in_(playlist.videos)).order_by(ordering)

    elif userlist == "history":
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(get_current_user().watched))))},
            value=MvVideo.extractor_data
        )
        videos = MvVideo.query.filter(MvVideo.extractor_data.in_(get_current_user().watched)).order_by(ordering)

    elif userlist == "watchlater":
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(get_current_user().watchlater))))},
            value=MvVideo.extractor_data
        )
        videos = MvVideo.query.filter(MvVideo.extractor_data.in_(get_current_user().watchlater)).order_by(ordering)

    else:
        vid_filter = [MvVideo.ytc_id == video.ytc_id, MvVideo.extractor_data != video_id]
        if video.published is not None:
            vid_filter.append(MvVideo.published <= video.published)
        videos = db_session.query(MvVideo).filter(*vid_filter) \
            .order_by(MvVideo.published.desc(), MvVideo.extractor_data.desc()).limit(PER_PAGE)

    IARCHIVEURL = current_app.config['IARCHIVEURL']
    IARCHIVEITEMURL = current_app.config['IARCHIVEITEMURL']
    video_url_short = IARCHIVEURL + video_id + "/"
    video_url_download = IARCHIVEITEMURL + video_id

    video_url = _resolve_video_url(video, video_id)

    playlist_titles = []
    not_in_watchlater = None

    if get_current_user() is not None:
        user = get_current_user()

        try:
            user.watched += [video.extractor_data]
        except Exception:
            user.watched = [video.extractor_data]

        user.watched = list(dict.fromkeys(user.watched))
        user.updated = datetime.now(timezone.utc)
        flag_modified(user, "watched")
        db_session.commit()

        if user.watchlater is None or (video_id not in user.watchlater):
            not_in_watchlater = True

        plists = db_session.query(Playlist).filter(Playlist.user_id == user.id)

        for plist in plists:
            if video_id not in plist.videos:
                playlist_titles.append(plist.title)

    #    if FLASH_MSG is not None:
    #        flash(Markup(FLASH_MSG), 'error')

    # FLASH_MSG = '<a href=' + video_url_download + ' class="alert-link" target="_blank" rel="noopener noreferrer" span
    # style="color: darkorange;">Download<a> preferred videos, Internet Archive is <a
    # href=https://archive.org/details/youtube-Gv4jjFgIP_g class="alert-link" target="_blank" rel="noopener
    # noreferrer" span style="color: darkorange;">limiting access on some items</a>'

    if NEW_FLASH_MSG is not None:
        flash(Markup(NEW_FLASH_MSG), 'error')
    else:
        if FLASH_MSG is not None:
            flash(Markup(FLASH_MSG), 'error')

    return render_template('video/video_item.html', video_url=video_url, video_url_short=video_url_short,
                           video_id=video_id, channel=channel, video=video, videos=videos, cat_id=cat_id, tags=tags,
                           playlist=playlist, userlist=userlist, not_in_watchlater=not_in_watchlater,
                           playlist_titles=playlist_titles, video_url_download=video_url_download)


def _get_next_video(video, playlist=None, userlist=None):
    """Return the extractor_data of the next video to play, or None."""
    next_video = None

    if playlist is not None:
        if playlist.videos and len(playlist.videos) > 1:
            existing = {r[0] for r in db_session.query(MvVideo.extractor_data)
                        .filter(MvVideo.extractor_data.in_(playlist.videos))}
            active = [v for v in playlist.videos if v in existing]
            if len(active) > 1 and video.extractor_data in active:
                idx = active.index(video.extractor_data)
                next_video = active[idx - 1]
                if not session.get('looplist') and idx == 0:
                    next_video = None

    elif userlist in ("history", "watchlater"):
        user = get_current_user()
        if user:
            user_list = user.watched if userlist == "history" else user.watchlater
            if user_list and len(user_list) > 1:
                existing = {r[0] for r in db_session.query(MvVideo.extractor_data)
                            .filter(MvVideo.extractor_data.in_(user_list))}
                active = [v for v in user_list if v in existing]
                if len(active) > 1 and video.extractor_data in active:
                    idx = active.index(video.extractor_data)
                    next_video = active[idx - 1]
                    if not session.get('looplist') and idx == 0:
                        next_video = None

    else:
        first_vid_pub = session.get('first_vid_pub')
        q = db_session.query(MvVideo.extractor_data).filter(MvVideo.ytc_id == video.ytc_id)
        if first_vid_pub is not None:
            q = q.filter(MvVideo.published <= first_vid_pub)
        channel_vids = q.order_by(MvVideo.published.desc(), MvVideo.extractor_data.desc()).limit(PER_PAGE)

        if channel_vids.count() > 1:
            vlist = [r[0] for r in channel_vids]
            vlist.reverse()
            try:
                idx = vlist.index(video.extractor_data)
            except Exception:
                idx = len(vlist)
            next_video = vlist.pop(idx - 1)
            try:
                vlist.remove(video.extractor_data)
            except Exception:
                pass
            if not session.get('looplist') and idx == 0:
                next_video = None

    return next_video


@bp.route('/embed/<video_id>')
def embed(video_id):
    if video_id is None:
        abort(404)
    video = db_session.execute(select(MvVideo).filter(MvVideo.extractor_data == video_id)).scalar()
    if video is None:
        abort(404)

    playlist_hash = request.args.get('playlist', None)
    userlist = request.args.get('userlist', None)

    video_url = _resolve_video_url(video, video_id)

    playlist = None
    if playlist_hash:
        playlist = Playlist.query.filter(Playlist.hashid == playlist_hash).scalar()
        if playlist is None:
            abort(404)

    next_video = _get_next_video(video, playlist=playlist, userlist=userlist)

    return render_template('video/video_embed.html', video_url=video_url, next_video=next_video,
                           playlist=playlist, userlist=userlist, video_id=video_id)


@bp.route('/api/ping-view/<video_id>', methods=['POST'])
def ping_view(video_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    header = request.headers.get('User-Agent')
    Thread(target=increment_video_counter, args=(video_id, ip, header)).start()
    return '', 204


@bp.route('/api/video-sources/<video_id>')
def video_sources_api(video_id):
    video = db_session.execute(select(MvVideo).filter(MvVideo.extractor_data == video_id)).scalar()
    if video is None:
        abort(404)

    playlist_hash = request.args.get('playlist', None)
    userlist = request.args.get('userlist', None)

    video_url = _resolve_video_url(video, video_id)

    session['first_vid_pub'] = video.published
    session.modified = True

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    header = request.headers.get('User-Agent')
    Thread(target=increment_video_counter, args=(video_id, ip, header)).start()

    playlist = None
    if playlist_hash:
        playlist = Playlist.query.filter(Playlist.hashid == playlist_hash).scalar()

    next_video = _get_next_video(video, playlist=playlist, userlist=userlist)

    next_watch_url = None
    if next_video:
        if playlist_hash:
            next_watch_url = f"/watch?v={next_video}&playlist={playlist_hash}"
        elif userlist:
            next_watch_url = f"/watch?v={next_video}&userlist={userlist}"
        else:
            next_watch_url = f"/watch?v={next_video}"

    return jsonify({'video_url': video_url, 'next_watch_url': next_watch_url})


def _search_impl(rawsearch, video_order, order_label, page):
    offset = ((int(page) - 1) * PER_PAGE)
    if rawsearch is None:
        abort(404)
    term = rawsearch.strip()

    if term.lower().partition("youtube.com/watch?v=")[2]:
        term = term.lower().partition("youtube.com/watch?v=")[2]
    elif term.lower().partition("youtube.com/channel/")[2]:
        term = term.lower().partition("youtube.com/channel/")[2]

    tsv = text("mv_video.document @@ websearch_to_tsquery(:search)")
    tsc = text("mv_channel.document @@ websearch_to_tsquery(:search)")
    tsp = text("mv_playlist.document @@ websearch_to_tsquery(:search)")
    tsu = text("mv_altcen_user.document @@ websearch_to_tsquery(:search)")
    rank_c = text("ts_rank(mv_channel.document, websearch_to_tsquery(:search)) DESC")
    rank_p = text("ts_rank(mv_playlist.document, websearch_to_tsquery(:search)) DESC")
    rank_u = text("ts_rank(mv_altcen_user.document, websearch_to_tsquery(:search)) DESC")

    videos = db_session.query(MvVideo).filter(tsv).order_by(video_order) \
        .limit(PER_PAGE).offset(offset).params(search=term).all()
    channels = db_session.query(MvChannel).filter(tsc).order_by(rank_c).params(search=term).all()
    searchplaylists = db_session.query(MvPlaylist).filter(MvPlaylist.public, tsp) \
        .order_by(rank_p).params(search=term).all()
    altcen_users = db_session.query(MvAltcenUser).filter(MvAltcenUser.public, tsu) \
        .order_by(rank_u).limit(PER_PAGE).offset(offset).params(search=term).all()

    videocount = db_session.query(func.count(MvVideo.extractor_data)).filter(tsv).params(search=term).scalar()
    channcount = db_session.query(func.count(MvChannel.ytc_id)).filter(tsc).params(search=term).scalar()
    searchplaylistcount = db_session.query(func.count(MvPlaylist.id)).filter(tsp).params(search=term).scalar()
    usercount = db_session.query(func.count(MvAltcenUser.id)).filter(MvAltcenUser.public, tsu) \
        .params(search=term).scalar()

    pagination = Pagination(page, PER_PAGE, videocount)

    watchlater = get_current_user().watchlater if get_current_user() else None

    playlist_ident = request.args.get('playlist', None)
    playlist = None
    if playlist_ident:
        channels = None
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    fv_ids = [p.featured_video_id for p in searchplaylists if p.featured_video_id]
    featured_search_videos = {}
    if fv_ids:
        fvs = MvVideo.query.filter(MvVideo.extractor_data.in_(fv_ids)).all()
        featured_search_videos = {fv.extractor_data: fv for fv in fvs}

    if not videos and page != 1:
        abort(404)
    return render_template('video/video_search.html', videos=videos, pagination=pagination,
                           usercount=usercount, channcount=channcount,
                           searchplaylistcount=searchplaylistcount, rawsearch=rawsearch,
                           searchplaylists=searchplaylists, altcen_users=altcen_users,
                           order=order_label, channels=channels, videocount=videocount,
                           watchlater=watchlater, playlist=playlist,
                           featured_search_videos=featured_search_videos)


@bp.route("/search", defaults={'page': 1})
@bp.route('/search/page/<int:page>')
def search(page):
    return _search_impl(request.args.get('q'),
                        text("ts_rank(mv_video.document, websearch_to_tsquery(:search)) DESC"),
                        'default', page)


@bp.route("/search/latest", defaults={'page': 1})
@bp.route('/search/latest/page/<int:page>')
def search_latest(page):
    return _search_impl(request.args.get('q'), MvVideo.id.desc(), 'latest', page)


@bp.route("/search/new", defaults={'page': 1})
@bp.route('/search/new/page/<int:page>')
def search_new(page):
    return _search_impl(request.args.get('q'), MvVideo.published.desc(), 'newest', page)


@bp.route("/search/popular", defaults={'page': 1})
@bp.route('/search/popular/page/<int:page>')
def search_popular(page):
    return _search_impl(request.args.get('q'), MvVideo.yt_views.desc(), 'popular', page)


@bp.route('/play-next', methods=['GET', 'POST'])
def play_next():
    get_playnext()
    if request.method == 'POST':
        data = json.loads(request.data)
        session['playnext'] = not session['playnext']
        return json.dumps({'playnext': session['playnext']})
    else:
        return json.dumps({'playnext': session['playnext']})


@bp.route("/test1")
def test1():
    video_id = 'b9xIyw4dQZo'
    video_id = '7-tUV0cnyv8'
    video_id = 'c7BJ-VgSumw'
    #    video_id = 'C4tT99haZXE'
    #    video_id = 't25ptPWc1NI'
    video_id = '0kX-1OOrU5M'  # orig ogv, mp4

    ia_url = "https://archive.org/download/youtube-" + video_id + "/" + video_id
    ac_url = "https://videos.altcensored.com/youtube-" + video_id + "/" + video_id

    #    return render_template('video/test1.html',video_url=ac_url)
    return render_template('video/video_embed_test.html', video_url=ac_url)


@bp.route("/test2")
def test2():
    video_id = 'b9xIyw4dQZo'
    video_id = '7-tUV0cnyv8'

    ia_url = "https://archive.org/download/youtube-" + video_id + "/" + video_id
    ia_url = "https://videos.altcensored.com/youtube-" + video_id + "/" + video_id

    return render_template('video/test2.html', ia_url=ia_url)
