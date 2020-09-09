from flask import (
    Blueprint, session, render_template, request, flash, redirect, url_for
)
from sqlalchemy import func
from hashids import Hashids
from .database import db_session
from .models import User, Playlist
from .pagination import Pagination
from .util import login_required
import datetime, random

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
#    playlist = Playlist.query.filter(Playlist.id) == (playlist_id).scalar()
    return render_template('playlist/playlist_item.html', playlist=playlist)


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

        dt = datetime.datetime.now(tz=None)
        playlist = Playlist (title=ftitle, id=hashid, user_id=user_id, created=dt, public=False,)
        db_session.add(playlist)
        db_session.commit()

    return render_template('playlist/playlist_create.html')