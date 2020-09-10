from flask import (
    Blueprint, session, render_template, request, flash, redirect, url_for
)
from sqlalchemy import func
from hashids import Hashids
from .database import db_session
from .models import User, Playlist
from .pagination import Pagination
from .util import login_required
import random, timeago, datetime
from datetime import timezone

bp = Blueprint('playlist', __name__, url_prefix='/playlist')

PER_PAGE = 24

def title_exists(ftitle):
#    if username == session['user']['username']:
#        return False
    user_id = session['user']['id']
#    if db_session.query(Playlist.title).filter(User.user_id) == (user_id).scalar() is not None:
    if db_session.query(Playlist.title).filter((Playlist.title) == (ftitle)).filter((Playlist.user_id) == (user_id)).scalar() is not None:
        return True

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    playlistcount = Playlist.query.filter(Playlist.public).count()
    playlists = Playlist.query.filter(Playlist.public).limit(PER_PAGE).offset(offset)
    if not playlists and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, playlistcount)

    return render_template('playlist/playlist_index.html', 
        pagination=pagination, playlistcount=playlistcount, playlists=playlists)


@bp.route('/<playlist>')
def item(playlist):
    playlist = Playlist.query.get(playlist)

    updated = playlist.updated
    now = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds = 60 * 3.4)
    timediff = timeago.format(updated, now)
#    timediff = (timeago.format('2016-05-27 12:12:03', '2016-05-27 12:12:12'))

    return render_template('playlist/playlist_item.html', playlist=playlist, timediff=timediff)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        ftitle = request.form['title']
        fprivacy = request.form['privacy']
        user_id = session['user']['id']

        if title_exists(ftitle):
            flash('Title already exists', 'error')
            return redirect(url_for('playlist.create'))

        hashids = Hashids(min_length=22)
        hashid = 'AC' + hashids.encode(random.getrandbits(104))

        now = datetime.now(timezone.utc)
        playlist = Playlist (title=ftitle, id=hashid, user_id=user_id, created=now, updated=now, public=False,)
        db_session.add(playlist)
        db_session.commit()

    return render_template('playlist/playlist_create.html')