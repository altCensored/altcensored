from flask import (
    Blueprint, session, render_template, request, flash
)
from sqlalchemy import func
from hashids import Hashids
from .database import db_session
from .models import User, Playlist
from .pagination import Pagination
from .auth import login_required
import datetime, random

bp = Blueprint('playlist', __name__, url_prefix='/playlist')

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    usercount = User.query.filter(User.public).count()
    users = User.query.filter(User.public).limit(PER_PAGE).offset(offset)
    if not users and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, usercount)

    return render_template('playlist/playlist_index.html', 
        pagination=pagination, usercount=usercount, users=users)


@bp.route('/<username>')
def item(username):
    user = User.query.filter(func.lower(User.username) == func.lower(username)).scalar()
    if not username and page != 1:
        abort(404)
    return render_template('playlist/playlist_item.html', user=user)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():

    if request.method == 'POST':
        ftitle = request.form['title']
        fprivacy = request.form['privacy']
        user_id = session['user']['id']

        hashids = Hashids(min_length=22)
        hashid = 'UU' + hashids.encode(random.getrandbits(104))

        dt = datetime.datetime.now(tz=None)
        playlist = Playlist (title=ftitle, id=hashid, user_id=user_id, created=dt, public=False,)
        db_session.add(playlist)
        db_session.commit()

    return render_template('playlist/playlist_create.html')