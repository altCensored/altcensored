from flask import (
    Blueprint, session, render_template, request, flash, redirect, url_for
)
from sqlalchemy import func
from hashids import Hashids
from flask_babelplus import lazy_gettext
import random, timeago, datetime
from datetime import timezone
from .database import db_session
from .models import User, Playlist
from .pagination import Pagination
from .util import login_required, str_to_bool, title_exists

bp = Blueprint('playlist', __name__, url_prefix='/playlist')

PER_PAGE = 24


@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'

    if session.get('user') is not None and order == session['user']['username']:
        user = User.query.filter(func.lower(User.username) == func.lower(order)).scalar()

        playlistcount = Playlist.query.filter(Playlist.public).filter(Playlist.user_id == user.id).count()
        playlists = Playlist.query.filter(Playlist.public)\
        .join(User,Playlist.user_id == User.id)\
        .filter(User.username == order)\
        .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    else:
        playlistcount = Playlist.query.filter(Playlist.public).count()
        playlists = Playlist.query.filter(Playlist.public)\
        .order_by(Playlist.id.desc()).limit(PER_PAGE).offset(offset)

    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html', 
        pagination=pagination, playlistcount=playlistcount, playlists=playlists, order=order)


@bp.route('/popular', defaults={'page': 1})
@bp.route('/popular/page/<int:page>')
def popular(page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'

    playlistcount = Playlist.query.filter(Playlist.public).count()
    playlists = Playlist.query.filter(Playlist.public)\
    .order_by(Playlist.view_counter.desc()).limit(PER_PAGE).offset(offset)

    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html', 
        pagination=pagination, playlistcount=playlistcount, playlists=playlists, order=order)


@bp.route('/<playlist>')
def item(playlist):
    playlist = Playlist.query.filter(Playlist.id == playlist).scalar()

    updated = playlist.updated
    now = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds = 60 * 3.4)
    timediff = timeago.format(updated, now)

    return render_template('playlist/playlist_item.html', playlist=playlist, timediff=timediff)


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
        playlist = Playlist (title=ftitle, description=fdescription, id=hashid, user_id=user_id, created=now, updated=now, public=fprivacy,)
        db_session.add(playlist)
        db_session.commit()

    return render_template('playlist/playlist_create.html')


@bp.route('/edit/<playlist>', methods=['GET', 'POST'])
@login_required
def edit(playlist):
    if request.method == 'POST':
        ftitle = request.form['title']
        fprivacy = str_to_bool(request.form['privacy'])
        user_id = session['user']['id']

        if title_exists(ftitle):
            flash('Title already exists', 'error')
            return redirect(url_for('playlist.create'))

        hashids = Hashids(min_length=22)
        hashid = 'AC' + hashids.encode(random.getrandbits(104))

        now = datetime.now(timezone.utc)
        playlist = Playlist (title=ftitle, id=hashid, user_id=user_id, created=now, updated=now, public=fprivacy)
        db_session.add(playlist)
        db_session.commit()

    return render_template('playlist/playlist_edit.html')


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
