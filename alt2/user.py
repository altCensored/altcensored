from flask import (
    Blueprint, session, render_template, flash, redirect, request, url_for
)
from sqlalchemy import func, case
from sqlalchemy.orm.attributes import flag_modified
from flask_babelplus import lazy_gettext
from .database import db_session
from .models import User, Mv_Video, Playlist, Counter
from .pagination import Pagination
from .util import login_required
import datetime

bp = Blueprint('user', __name__, url_prefix='/user' )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    usercount = User.query.filter(User.public).count()

    users = User.query.filter(User.public).order_by(User.id.desc()).limit(PER_PAGE).offset(offset)

    if not users and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, usercount)

    return render_template('user/user_index.html', 
        pagination=pagination, usercount=usercount, users=users, order=order)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    usercount = User.query.filter(User.public).count()

    users = User.query.filter(User.public).order_by(User.view_counter.desc()).limit(PER_PAGE).offset(offset)

    if not users and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, usercount)

    return render_template('user/user_index.html', 
        pagination=pagination, usercount=usercount, users=users, order=order)


@bp.route('/<username>')
def item(username):
    user = User.query.filter(func.lower(User.username) == func.lower(username)).scalar()
    playlistcount = Playlist.query.filter(Playlist.public).filter(Playlist.user_id == user.id).count()

    playlist = Playlist.query.filter(Playlist.user_id == user.id).order_by(Playlist.view_counter.desc()).first()

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
        counter = Counter (hash=myhash)
        db_session.add(counter)
        db_session.commit()

        user.view_counter = user.view_counter + 1
        flag_modified(user, "view_counter")
        db_session.commit()

    if not username and page != 1:
        abort(404)
    return render_template('user/user_item.html', user=user, playlistcount=playlistcount,\
     historycount=historycount, watchlatercount=watchlatercount, playlist=playlist)


@bp.route('/history', defaults={'page': 1})
@bp.route('/history/page/<int:page>')
@login_required
def history(page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = request.args.get('playlist', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
    user.watched = list(dict.fromkeys(user.watched))

    try:
        ordering = case(
            {id: index for index, id in reversed(list(enumerate(reversed(user.watched))))},
            value=Mv_Video.id
         )
        videos = Mv_Video.query.filter(Mv_Video.id.in_(user.watched)).order_by(ordering).limit(PER_PAGE).offset(offset)
        videocount=len(user.watched)
        pagination = Pagination(page, PER_PAGE, videocount)  
        return render_template('user/user_history_index.html', pagination=pagination,\
         videos=videos, videocount=videocount, playlist=playlist, watchlater=user.watchlater)
    except:
        flash('History Empty', 'success')
        return redirect(request.args.get('original_url', '/'))


@bp.route('/remove_video_history')
@login_required
def remove_video_history():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    video = Mv_Video.query.get(video_id)
    if video.id in user.watched:
        user.watched = list(dict.fromkeys(user.watched))
        user.watched.remove(video.id)
        db_session.commit()
    return redirect(request.args.get('original_url', '/'))


@bp.route('/clear_history', methods=['GET', 'POST'])
@login_required
def clear_history():
    user = User.query.filter(User.email == session['user']['email']).scalar()
    if not user.watched:
        flash('History Empty', 'success')
        return redirect(request.args.get('original_url', '/'))
    l_msg = lazy_gettext('Clear History')
    message = l_msg + ' ?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(User.email == session['user']['email']).one()
            user.watched = None
            flag_modified(user, "watched")
            db_session.commit()
            flash('History Cleared', 'success')
        else:
            flash('History Not Cleared', 'error')
        return redirect(request.args.get('original_url', '/'))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/watchlater', defaults={'page': 1})
@bp.route('/watchlater/page/<int:page>')
@login_required
def watchlater(page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = request.args.get('playlist', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()

    try:
        ordering = case(
            {id: index for index, id in reversed(list(enumerate(reversed(user.watchlater))))},
            value=Mv_Video.id
         )
        videos = Mv_Video.query.filter(Mv_Video.id.in_(user.watchlater)).order_by(ordering).limit(PER_PAGE).offset(offset)
        videocount=len(user.watchlater)
        pagination = Pagination(page, PER_PAGE, videocount)  
        return render_template('user/user_watchlater_index.html', pagination=pagination, \
            videos=videos, videocount=videocount, playlist=playlist, watchlater=user.watchlater)
    except:
        flash('No Watch Later Available', 'success')
        return redirect(request.args.get('original_url', '/'))


@bp.route('/add_video_watchlater')
@login_required
def add_video_watchlater():
    video_id = request.args.get('v', None)
    video = Mv_Video.query.get(video_id)
    user = db_session.query(User).filter(User.email == session['user']['email']).one()
    try:
        user.watchlater += [video.id]
    except:
        user.watchlater = [video.id]
    flag_modified(user, "watchlater")
    db_session.commit()
    return redirect(request.args.get('original_url', '/'))


@bp.route('/remove_video_watchlater')
@login_required
def remove_video_watchlater():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    video = Mv_Video.query.get(video_id)
    if video.id in user.watchlater:
        user.watchlater = list(dict.fromkeys(user.watchlater))
        user.watchlater.remove(video.id)
        db_session.commit()
    return redirect(request.args.get('original_url', '/'))


@bp.route('/clear_watchlater', methods=['GET', 'POST'])
@login_required
def clear_watchlater():
    user = User.query.filter(User.email == session['user']['email']).scalar()
    if not user.watchlater:
        flash('WatchLater Empty', 'success')
        return redirect(request.args.get('original_url', '/'))
    l_msg = lazy_gettext('Clear WatchLater')
    message = l_msg + ' ?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(User.email == session['user']['email']).one()
            user.watchlater = None
            flag_modified(user, "watchlater")
            db_session.commit()
            flash('WatchLater Cleared', 'success')
            return redirect(request.args.get('original_url', '/'))
        else:
            flash('WatchLater Not Cleared', 'error')
            return redirect(request.args.get('original_url', '/'))
    return render_template('widgets/widgets_confirm.html', message=message)


@bp.route('/playlist', defaults={'page': 1})
@bp.route('/playlist/page/<int:page>')
@login_required
def playlist(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = request.args.get('order','newest')
    user = User.query.filter(User.email == session['user']['email']).scalar()

    playlistcount = Playlist.query.filter(Playlist.user_id == user.id).count()

    if order =='popular':
        playlists = Playlist.query.filter(Playlist.user_id == session['user']['id'])\
        .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset)
    else:
        playlists = Playlist.query.filter(Playlist.user_id == session['user']['id'])\
        .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('user/user_playlist_index.html', 
        pagination=pagination, playlistcount=playlistcount, playlists=playlists, order=order)