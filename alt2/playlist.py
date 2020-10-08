from flask import (
    Blueprint, session, render_template, request, flash, redirect, url_for
)
from sqlalchemy import func, case
from sqlalchemy.orm.attributes import flag_modified
from hashids import Hashids
from flask_babelplus import lazy_gettext
import random, timeago, datetime
from datetime import timezone
from .database import db_session
from .models import User, Playlist, Mv_Video, Counter
from .pagination import Pagination
from .util import login_required, str_to_bool, title_exists

bp = Blueprint('playlist', __name__, url_prefix='/playlist')

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = request.args.get('order','newest')
    playlistcount = Playlist.query.filter(Playlist.public).count()

    if session.get('user') is not None and order == session['user']['username']:
        user = User.query.filter(func.lower(User.username) == func.lower(order)).scalar()

        playlistcount = Playlist.query.filter(Playlist.public).filter(Playlist.user_id == user.id).count()
        playlists = Playlist.query.filter(Playlist.public)\
        .join(User,Playlist.user_id == User.id)\
        .filter(User.username == order)\
        .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    elif order =='popular':
        playlists = Playlist.query.filter(Playlist.public)\
        .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset)
    else:
        playlists = Playlist.query.filter(Playlist.public)\
        .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html', 
        pagination=pagination, playlistcount=playlistcount, playlists=playlists, order=order)


@bp.route('/<playlist>', defaults={'page': 1})
@bp.route('/<playlist>/page/<int:page>')
def item(playlist,page):
    offset = ((int(page)-1) * PER_PAGE)
    playlist = Playlist.query.filter(Playlist.hashid == playlist).scalar()
    button = request.args.get('button', None)

    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.email == session['user']['email']).scalar()
        if user.watchlater:
            watchlater=user.watchlater

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    header = request.headers.get('User-Agent')
    today = str(datetime.date.today())
    myhash=hash(ip+header+today+str(playlist))

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
        pagination = Pagination(page, PER_PAGE, videocount)
    else:
        videos = []
        videocount = 0
        pagination = 0

    playlist.video_count = videocount
    flag_modified(playlist, "video_count")
    db_session.commit()


    return render_template('playlist/playlist_item.html', playlist=playlist, timediff=timediff,\
        videos=videos, videocount=videocount, pagination=pagination, watchlater=watchlater, button=button)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        ftitle = request.form['title']
        fdescription = request.form['description']        
        fprivacy = str_to_bool(request.form['privacy'])
        user_id = session['user']['id']

        if title_exists(ftitle):
            flash('Title already exists', 'error')
            return redirect(url_for('playlist.create'))

        hashids = Hashids(min_length=22)
        hashid = 'AC' + hashids.encode(random.getrandbits(104))

        now = datetime.datetime.now(timezone.utc)
        empty_list = []
        playlist = Playlist (title=ftitle, description=fdescription, hashid=hashid,\
         user_id=user_id, created=now, updated=now, public=fprivacy, view_counter=0, \
         video_count=0, videos=empty_list)

        db_session.add(playlist)
        db_session.commit()

        return redirect(url_for('playlist.item', playlist=hashid))
        
    return render_template('playlist/playlist_create_edit.html')


@bp.route('/edit/<playlist>', methods=['GET', 'POST'])
@login_required
def edit(playlist):
    playlist = Playlist.query.get(playlist)

    if request.method == 'POST':
        ftitle = request.form['title']
        fdescription = request.form['description']        
        fprivacy = str_to_bool(request.form['privacy'])

        if ftitle != playlist.title and title_exists(ftitle):
            flash('Title already exists', 'error')
            return redirect(url_for('playlist.create'))

        now = datetime.datetime.now(timezone.utc)
        playlist.title = ftitle
        playlist.description = fdescription
        playlist.public = fprivacy
        db_session.commit()
        return redirect(url_for('playlist.item', playlist=playlist.hashid))

    return render_template('playlist/playlist_create_edit.html', playlist=playlist)


@bp.route('/add_video_playlist')
@login_required
def add_video_playlist():
    playlist_hashid = request.args.get('playlist', None)
    video_id = request.args.get('v', None)
    video = Mv_Video.query.get(video_id)
    playlist = Playlist.query.filter(Playlist.hashid == playlist_hashid).scalar()
    try:
        playlist.videos += [video.extractor_data]

    except:
        playlist.videos = [video.extractor_data]

    if not playlist.featured_video:
        playlist.featured_video = {
        "extractor_data": video_id,
        "title": video.title
        }

    flag_modified(playlist, "videos")
    db_session.commit()

    return redirect(request.args.get('original_url', '/'))


@bp.route('/remove_video_playlist')
@login_required
def remove_video_playlist():
    playlist_hashid = request.args.get('playlist', None)
    video_id = request.args.get('v', None)
    video = Mv_Video.query.get(video_id)
    playlist = Playlist.query.filter(Playlist.hashid == playlist_hashid).scalar()

    if video.extractor_data in playlist.videos:
        playlist.videos = list(dict.fromkeys(playlist.videos))
        playlist.videos.remove(video.extractor_data)

        if video_id == playlist.featured_video['extractor_data']:
            playlist.featured_video = None

            if playlist.videos:
                replacement_video_id = playlist.videos[0]
                video = Mv_Video.query.get(replacement_video_id)
                playlist.featured_video = {
                "extractor_data": replacement_video_id,
                "title": video.title
                }

        db_session.commit()

    return redirect(request.args.get('original_url', '/'))


@bp.route('/delete/<playlist>', methods=['GET', 'POST'])
@login_required
def delete(playlist):
    playlistobj = Playlist.query.get(playlist)
    l_msg = lazy_gettext('Remove playlist')
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
            return redirect(url_for('playlist.index'))

    return render_template('widgets/widgets_confirm.html', message=message)