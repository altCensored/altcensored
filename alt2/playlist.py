from flask import (
    Blueprint, session, render_template, request, flash, redirect, url_for, app
)
from werkzeug.exceptions import abort
from sqlalchemy import func, case
from sqlalchemy.orm.attributes import flag_modified
from hashids import Hashids
from flask_babelplus import lazy_gettext
import random, timeago, datetime, json
from datetime import timezone
from .database import db_session
from .models import User, Playlist, Mv_Video, Counter
from .pagination import Pagination
from . import util
from .util import (
    login_required, str_to_bool, title_exists, get_playlistcount
    )
bp = Blueprint('playlist', __name__, url_prefix='/playlist')

no_profanity = lazy_gettext('Profanity forbidden')
title_exist = lazy_gettext('Title exists')

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    playlists = Playlist.query.filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
        .order_by(Playlist.updated.desc()).limit(PER_PAGE).offset(offset)
#    playlists = playlists_newest(PER_PAGE, offset)
    if not playlists and page != 1:
        abort(404)
    playlistcount = get_playlistcount()
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html',
                           pagination=pagination, playlists=playlists, playlistcount=playlistcount, order=order)

@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    playlists = Playlist.query.filter(Playlist.public).filter(Playlist.featured_video.isnot(None)) \
        .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset)
#    playlists = playlists_popular(PER_PAGE, offset)
    if not playlists and page != 1:
        abort(404)
    playlistcount = get_playlistcount()
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html',
                           pagination=pagination, playlists=playlists, playlistcount=playlistcount, order=order)

@bp.route('/<playlist>', defaults={'page': 1})
@bp.route('/<playlist>/page/<int:page>')
def item(playlist,page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
#    playlist = playlisti(playlist)

    if playlist is None:
        abort(404)
    button = request.args.get('button', None)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater=user.watchlater

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    header = request.headers.get('User-Agent')
    today = str(datetime.date.today())
    myhash = hash(ip+header+today+str(playlist.hashid))

    if Counter.query.filter(Counter.hash == myhash).scalar() is None:
        counter = Counter (hash=myhash)
        db_session.add(counter)
        db_session.commit()

        playlist.view_counter = playlist.view_counter + 1
        flag_modified(playlist, "view_counter")
        db_session.commit()

    updated = playlist.updated
    now = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds = 60 * 3.4)
    timediff = timeago.format(updated, now)

    if playlist.videos:
        ordering = case(
            {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(playlist.videos))))},
            value=Mv_Video.extractor_data
        )
        videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(playlist.videos)).order_by(ordering).limit(PER_PAGE).offset(offset)
        videocount = db_session.query(func.count(Mv_Video.id)).filter(Mv_Video.extractor_data.in_(playlist.videos)).scalar()
#        videocount = playlisti_videocount(playlist)
#        videos = playlisti_videos(playlist, ordering, PER_PAGE, offset)

        pagination = Pagination(page, PER_PAGE, videocount)
    else:
        videos = []
        videocount = 0
        pagination = 0

    playlist.video_count = videocount
    flag_modified(playlist, "video_count")
    db_session.commit()

    return render_template('playlist/playlist_item.html', playlist=playlist, timediff=timediff, \
                           videos=videos, videocount=videocount, pagination=pagination, watchlater=watchlater, button=button)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        ftitle = request.form['title']
        fdescription = request.form['description']
        fpublic = str_to_bool(request.form['public'])
        user_id = session['user']['id']

        if title_exists(ftitle):
            flash(title_exist, 'error')
            return redirect(url_for('playlist.create'))

        if util.contains_profanity(ftitle):
            flash(no_profanity, 'error')
            return redirect(url_for('playlist.create'))

        if util.contains_profanity(fdescription):
            flash(no_profanity, 'error')
            return redirect(url_for('playlist.create'))


        hashids = Hashids(min_length=22)
        hashid = 'AC' + hashids.encode(random.getrandbits(104))

        now = datetime.datetime.now(timezone.utc)
        empty_list = []
        playlist = Playlist (title=ftitle, description=fdescription, hashid=hashid, \
                             user_id=user_id, created=now, updated=now, public=fpublic, view_counter=0, \
                             video_count=0, videos=empty_list)

        db_session.add(playlist)
        db_session.commit()

        return redirect(url_for('playlist.item', playlist=hashid))

    return render_template('playlist/playlist_item_create_edit.html')


@bp.route('/edit/<playlist>', methods=['GET', 'POST'])
@login_required
def edit(playlist):
    playlist = Playlist.query.get(playlist)

    if request.method == 'POST':
        ftitle = request.form['title']
        fdescription = request.form['description']
        fpublic = str_to_bool(request.form['public'])

        if util.contains_profanity(ftitle):
            flash(no_profanity, 'error')
            return redirect(url_for('playlist.edit', playlist=playlist.id))

        if util.contains_profanity(fdescription):
            flash(no_profanity, 'error')
            return redirect(url_for('playlist.edit', playlist=playlist.id))

        if ftitle != playlist.title and title_exists(ftitle):
            flash(title_exist, 'error')
            return redirect(url_for('playlist.edit', playlist=playlist.id))

        now = datetime.datetime.now(timezone.utc)
        playlist.updated = now
        playlist.title = ftitle
        playlist.description = fdescription
        playlist.public = fpublic
        db_session.commit()
        return redirect(url_for('playlist.item', playlist=playlist.hashid))

    return render_template('playlist/playlist_item_create_edit.html', playlist=playlist)


@bp.route('/add_video_playlist', methods=['GET', 'POST'])
@login_required
def add_video_playlist():
    if request.method == 'POST':
        video_id = request.form['v']
        playlist_ident = request.form['playlist_title']
        try:
            playlist = Playlist.query.filter((Playlist.user_id == session['user']['id']), Playlist.title == playlist_ident).scalar()
        except:
            app.logging.error('playlist POST query failed. user: %s, playlist_ident: %s, video: %s', session['user']['id'], playlist_ident, video_id)
            abort(500)

    else:
        video_id = request.args.get('v', None)
        playlist_ident = request.args.get('playlist', None)
        playlist = Playlist.query.filter(Playlist.hashid == playlist_ident).scalar()

    if playlist is None:
        app.logging.error('playlist is NONE. user: %s, playlist_ident: %s, video: %s', session['user']['id'], playlist_ident, video_id)
        abort(500)


    if playlist_ident == 'add_to_watchlater':
        user = User.query.get(session['user']['id'])

        if user.watchlater is not None:
            if not video_id in user.watchlater:
                user.watchlater = list(dict.fromkeys(user.watchlater))
                user.watchlater.append(video_id)

        if user.watchlater is None:
            user.watchlater = []
            user.watchlater.append(video_id)

        flag_modified(user, "watchlater")
        db_session.commit()
        return redirect(url_for('video.watch', v=video_id ))

    if playlist.videos is not None:
        if not video_id in playlist.videos:
            playlist.videos = list(dict.fromkeys(playlist.videos))
            playlist.videos.append(video_id)

    if playlist.videos is None:
        playlist.videos = []
        playlist.videos.append(video_id)

    if not playlist.featured_video:
        video = Mv_Video.query.get(video_id)
        playlist.featured_video = {
            "pl_id": playlist.id,
            "pl_title": playlist.title,
            "extractor_data": video_id,
            "title": video.title
        }

    now = datetime.datetime.now(timezone.utc)
    playlist.updated = now
    flag_modified(playlist, "videos")
    db_session.commit()

    if request.method == 'POST':
        return redirect(url_for('video.watch', v=video_id ))

    return redirect(request.args.get('original_url', '/'))


@bp.route('/add_video_playlist_post', methods=['GET', 'POST'])
@login_required
def add_video_playlist_post():
    if request.method == 'POST':
        data = json.loads(request.data)
        v = data['v']
        p = data['p']
        playlist = Playlist.query.filter(Playlist.hashid == p).scalar()

        if not v in playlist.videos:
            playlist.videos = list(dict.fromkeys(playlist.videos))
            playlist.videos.append(v)

        if not playlist.featured_video:
            video = Mv_Video.query.get(v)
            playlist.featured_video = {
                "pl_id": playlist.id,
                "pl_title": playlist.title,
                "extractor_data": video.extractor_data,
                "title": video.title
            }

        now = datetime.datetime.now(timezone.utc)
        playlist.updated = now
        flag_modified(playlist, "videos")
        db_session.commit()

        return json.dumps({'v': v})
    else:
        return json.dumps({'v': v})


@bp.route('/remove_video_playlist')
@login_required
def remove_video_playlist():
    playlist_hashid = request.args.get('playlist', None)
    video_ext = request.args.get('v', None)
    playlist = Playlist.query.filter(Playlist.hashid == playlist_hashid).scalar()

    if video_ext in playlist.videos:
        playlist.videos = list(dict.fromkeys(playlist.videos))
        playlist.videos.remove(video_ext)

        if video_ext == playlist.featured_video['extractor_data']:
            playlist.featured_video = None

            if playlist.videos:
                replacement_video_id = playlist.videos[0]
                video = Mv_Video.query.get(replacement_video_id)
                playlist.featured_video = {
                    "pl_id": playlist.id,
                    "pl_title": playlist.title,
                    "extractor_data": replacement_video_id,
                    "title": video.title
                }

        now = datetime.datetime.now(timezone.utc)
        playlist.updated = now
        flag_modified(playlist, "videos")
        db_session.commit()

    return redirect(request.args.get('original_url', '/'))


@bp.route('/delete/<playlist>', methods=['GET', 'POST'])
@login_required
def delete(playlist):
    playlistobj = Playlist.query.get(playlist)
    l_msg = lazy_gettext('Remove Playlist')
    item_quoted = (f'"{playlistobj.title}"')
    message = l_msg + ' ' + item_quoted + '?'

    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            playlist = db_session.query(Playlist).filter(Playlist.id == playlist).one()
            db_session.delete(playlist)
            db_session.commit()
            flash('Playlist ' + item_quoted + ' removed', 'success')
            return redirect(url_for('playlist.index'))
        else:
            flash('Playlist ' + item_quoted + ' NOT removed', 'error')
            return redirect(url_for('user.playlist', playlist=playlist))

    return render_template('widgets/widgets_confirm.html', message=message)