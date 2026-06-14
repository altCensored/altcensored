import logging
from flask import (
    Blueprint, session, render_template, flash, redirect, request, url_for, abort)

logger = logging.getLogger(__name__)
from sqlalchemy import func, case
from sqlalchemy.orm.attributes import flag_modified
from flask_babelplus import lazy_gettext
from .database import db_session
from .models import User, Mv_Video, Playlist, Counter
from .pagination import Pagination
from .util import login_required, get_usercount, users_newest, users_popular
from . import config

import datetime, json

bp = Blueprint('user', __name__, url_prefix='/user' )

PER_PAGE = 24
url_orig = 'original_url'


@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
#    users = User.query.filter(User.public).order_by(User.id.desc()).limit(PER_PAGE).offset(offset)
    users = users_newest(PER_PAGE, offset)
    if not users and page != 1:
        abort(404)
    get_usercount()
    pagination = Pagination(page, PER_PAGE, session['usercount'])

    return render_template('user/user_index.html', pagination=pagination, users=users, order=order)

@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page) - 1) * PER_PAGE)
    order = 'popular'
#    users = User.query.filter(User.public).order_by(User.view_counter.desc()).limit(PER_PAGE).offset(offset)
    users = users_popular(PER_PAGE, offset)
    if not users and page != 1:
        abort(404)
    usercount = get_usercount()
    pagination = Pagination(page, PER_PAGE, usercount)

    return render_template('user/user_index.html', pagination=pagination, users=users, order=order)

@bp.route('/<username>')
def item(username):
    user = User.query.filter(func.lower(User.username) == func.lower(username)).scalar()
#    user = useri(username)
    if user is None:
        flash(lazy_gettext('User unknown'), 'error')
        return redirect(request.args.get(url_orig, '/'))

    if session.get('user') is not None and username == session['user']['username']:
        playlists = Playlist.query.filter((Playlist.public),(Playlist.user_id == user.id)) \
            .join(User, Playlist.user_id == User.id) \
            .filter(Playlist.user_id == user.id) \
            .order_by(Playlist.id.desc())
        playlistcount = playlists.count()

    else:
        playlists = Playlist.query.filter((Playlist.public),(Playlist.user_id == user.id), \
                                          (Playlist.featured_video_id.isnot(None))) \
            .join(User, Playlist.user_id == User.id) \
            .filter(Playlist.user_id == user.id) \
            .order_by(Playlist.id.desc())
        playlistcount = playlists.count()

    if user.watched is None:
        historycount = 0
    else:
        historycount=len(user.watched)
    if user.watchlater is None:
        watchlatercount = 0
    else:
        watchlatercount=len(user.watchlater)

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    header = request.headers.get('User-Agent')
    today = str(datetime.date.today())
    myhash=hash(ip+header+today+username)

    if Counter.query.filter(Counter.hash == myhash).scalar() is None:
        counter = Counter(hash=myhash)
        db_session.add(counter)
        user.view_counter = user.view_counter + 1
        flag_modified(user, "view_counter")
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

    if not username and page != 1:
        abort(404)
    playlists = list(playlists)
    fv_ids = [p.featured_video_id for p in playlists if p.featured_video_id]
    featured_videos = {}
    if fv_ids:
        fvs = Mv_Video.query.filter(Mv_Video.extractor_data.in_(fv_ids)).all()
        featured_videos = {fv.extractor_data: fv for fv in fvs}
    return render_template('user/user_item.html', user=user, playlistcount=playlistcount, \
                           historycount=historycount, watchlatercount=watchlatercount, playlists=playlists,
                           featured_videos=featured_videos)


@bp.route('/history', defaults={'page': 1})
@bp.route('/history/page/<int:page>')
@login_required
def history(page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = request.args.get('playlist', None)
    user = User.query.filter(User.id == session['user']['id']).scalar()
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()

    if not user.watched:
        hist_empty = lazy_gettext('History Empty')
        flash(hist_empty, 'success')
        return redirect(request.args.get(url_orig, '/'))

    ordering = case(
        {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watched))))},
        value=Mv_Video.extractor_data
    )
    videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watched)).order_by(ordering).limit(PER_PAGE).offset(offset)
    videocount = len(user.watched)
    pagination = Pagination(page, PER_PAGE, videocount)
    return render_template('user/user_history_index.html', pagination=pagination,
                           videos=videos, videocount=videocount, playlist=playlist, watchlater=user.watchlater)


@bp.route('/remove_video_history')
@login_required
def remove_video_history():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.id == session['user']['id']).scalar()
    if user.watched and video_id in user.watched:
        user.watched = list(dict.fromkeys(user.watched))
        user.watched.remove(video_id)
        user.updated = datetime.datetime.now(datetime.timezone.utc)
        flag_modified(user, "watched")
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
            flash(lazy_gettext('Error removing video from history'), 'error')
    return redirect(request.args.get(url_orig, '/'))


@bp.route('/clear_history', methods=['GET', 'POST'])
@login_required
def clear_history():
    user = User.query.filter(User.id == session['user']['id']).scalar()
    if not user.watched:
        hist_empty = lazy_gettext('History Empty')
        flash(hist_empty, 'success')
        return redirect(request.args.get(url_orig, '/'))
    l_msg = lazy_gettext('Clear History')
    message = l_msg + ' ?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = User.query.filter(User.id == session['user']['id']).scalar()
            user.watched = []
            user.updated = datetime.datetime.now(datetime.timezone.utc)
            flag_modified(user, "watched")
            try:
                db_session.commit()
                flash(lazy_gettext('History Cleared'), 'success')
            except Exception:
                db_session.rollback()
                flash(lazy_gettext('Error clearing history'), 'error')
        else:
            hist_not_cleared = lazy_gettext('History Not Cleared')
            flash(hist_not_cleared, 'error')
        return redirect(url_for('user.item', username=session['user']['username']))

    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/watchlater', defaults={'page': 1})
@bp.route('/watchlater/page/<int:page>')
@login_required
def watchlater(page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = request.args.get('playlist', None)
    user = User.query.filter(User.id == session['user']['id']).scalar()
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()

    if not user.watchlater:
        no_watch = lazy_gettext('WatchLater Empty')
        flash(no_watch, 'success')
        return redirect(request.args.get(url_orig, '/'))

    ordering = case(
        {extractor_data: index for index, extractor_data in reversed(list(enumerate(reversed(user.watchlater))))},
        value=Mv_Video.extractor_data
    )
    videos = Mv_Video.query.filter(Mv_Video.extractor_data.in_(user.watchlater)).order_by(ordering).limit(PER_PAGE).offset(offset)
    videocount = len(user.watchlater)
    pagination = Pagination(page, PER_PAGE, videocount)
    return render_template('user/user_watchlater_index.html', pagination=pagination,
                           videos=videos, videocount=videocount, playlist=playlist, watchlater=user.watchlater)


@bp.route('/add_video_watchlater')
@login_required
def add_video_watchlater():
    video_id = request.args.get('v', None)
#    video = Mv_Video.query.get(video_id)
    user = User.query.filter(User.id == session['user']['id']).scalar()

    if user.watchlater is None:
        user.watchlater = [video_id]
    elif video_id not in user.watchlater:
        user.watchlater.append(video_id)
    user.updated = datetime.datetime.now(datetime.timezone.utc)
    flag_modified(user, "watchlater")
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        flash(lazy_gettext('Error updating watchlater'), 'error')
    return redirect(request.args.get(url_orig, '/'))


@bp.route('/add_video_watchlater_post', methods=['GET', 'POST'])
@login_required
def add_video_watchlater_post():
    if request.method == 'POST':
        data = json.loads(request.data)
        v = data['v']
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater is None:
            user.watchlater = [v]
        elif v not in user.watchlater:
            user.watchlater.append(v)
        user.updated = datetime.datetime.now(datetime.timezone.utc)
        flag_modified(user, "watchlater")
        try:
            db_session.commit()
            return json.dumps({'v': v})
        except Exception:
            db_session.rollback()
            return json.dumps({'error': 'db error'}), 500
    return json.dumps({})


@bp.route('/remove_video_watchlater')
@login_required
def remove_video_watchlater():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.id == session['user']['id']).scalar()
    if user.watchlater and video_id in user.watchlater:
        user.watchlater = list(dict.fromkeys(user.watchlater))
        user.watchlater.remove(video_id)
        user.updated = datetime.datetime.now(datetime.timezone.utc)
        flag_modified(user, "watchlater")
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()
            flash(lazy_gettext('Error updating watchlater'), 'error')
    return redirect(request.args.get(url_orig, '/'))


@bp.route('/clear_watchlater', methods=['GET', 'POST'])
@login_required
def clear_watchlater():
    user = User.query.filter(User.id == session['user']['id']).scalar()
    if not user.watchlater:
        watch_empty = lazy_gettext('WatchLater Empty')
        flash(watch_empty, 'success')
        return redirect(request.args.get(url_orig, '/'))
    l_msg = lazy_gettext('Clear WatchLater')
    message = l_msg + ' ?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = User.query.filter(User.id == session['user']['id']).scalar()
            user.watchlater.clear()
            user.updated = datetime.datetime.now(datetime.timezone.utc)
            flag_modified(user, "watchlater")
            try:
                db_session.commit()
                flash(lazy_gettext('WatchLater Cleared'), 'success')
            except Exception:
                db_session.rollback()
                flash(lazy_gettext('Error clearing watchlater'), 'error')
            return redirect(url_for('user.item', username=session['user']['username']))

        else:
            watch_not_clear = lazy_gettext('WatchLater Not Cleared')
            flash(watch_not_clear, 'error')
            return redirect(url_for('user.item', username=session['user']['username']))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/playlist', defaults={'page': 1})
@bp.route('/playlist/page/<int:page>')
@login_required
def playlist(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = request.args.get('order','newest')
    user = User.query.filter(User.id == session['user']['id']).scalar()

    playlistcount = Playlist.query.filter(Playlist.user_id == user.id).count()

    if order =='popular':
        playlists = Playlist.query.filter(Playlist.user_id == session['user']['id']) \
            .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset)
    else:
        playlists = Playlist.query.filter(Playlist.user_id == session['user']['id']) \
            .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    playlists = list(playlists)
    fv_ids = [p.featured_video_id for p in playlists if p.featured_video_id]
    featured_videos = {}
    if fv_ids:
        fvs = Mv_Video.query.filter(Mv_Video.extractor_data.in_(fv_ids)).all()
        featured_videos = {fv.extractor_data: fv for fv in fvs}
    return render_template('user/user_playlist_index.html',
                           pagination=pagination, playlistcount=playlistcount, playlists=playlists,
                           order=order, featured_videos=featured_videos)