from flask import (
    Blueprint, session, render_template, flash, redirect, request, url_for
)

from sqlalchemy import func, case
from sqlalchemy.orm.attributes import flag_modified
from flask_babelplus import lazy_gettext
from .database import db_session
from .models import User, Mv_Video
from .pagination import Pagination
from .util import login_required

bp = Blueprint('user', __name__, url_prefix='/user' )

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

    return render_template('user/user_index.html', 
        pagination=pagination, usercount=usercount, users=users)

@bp.route('/<username>')
def item(username):
    user = User.query.filter(func.lower(User.username) == func.lower(username)).scalar()

    if not username and page != 1:
        abort(404)
    return render_template('user/user_item.html', user=user)


@bp.route('/history', defaults={'page': 1})
@bp.route('/history/page/<int:page>')
@login_required
def history(page):
    offset = ((int(page)-1) * PER_PAGE)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    try:
        ordering = case(
            {id: index for index, id in reversed(list(enumerate(reversed(user.watched))))},
            value=Mv_Video.id
         )
        videos = Mv_Video.query.filter(Mv_Video.id.in_(user.watched)).order_by(ordering).limit(PER_PAGE).offset(offset)
        videocount = db_session.query(func.count(Mv_Video.id)).filter(Mv_Video.id.in_(user.watched)).scalar()
        pagination = Pagination(page, PER_PAGE, videocount)  
        return render_template('user/user_history_index.html', pagination=pagination, videos=videos, videocount=videocount)
    except:
        flash('No History Available', 'success')
        return redirect('/')

@bp.route('/add_video')
@login_required
def add_video():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    video = Mv_Video.query.get(video_id)
    if video.id in user.watched:
        user.watched.remove(video.id)
        flag_modified(user, "watched")
        db_session.commit()
    return redirect(url_for('user.history'))


@bp.route('/remove_video')
@login_required
def remove_video():
    video_id = request.args.get('v', None)
    user = User.query.filter(User.email == session['user']['email']).scalar()
    video = Mv_Video.query.get(video_id)
    if video.id in user.watched:
        user.watched.remove(video.id)
        flag_modified(user, "watched")
        db_session.commit()
    return redirect(url_for('user.history'))


@bp.route('/clear_watch_history', methods=['GET', 'POST'])
@login_required
def clear_watch_history():
    user = User.query.filter(User.email == session['user']['email']).scalar()
    if not user.watched:
        flash('No History Available', 'success')
        return redirect('/')
    l_msg = lazy_gettext('Clear History')
    message = l_msg + ' ?'
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(User.email == session['user']['email']).one()
            user.watched = None
            flag_modified(user, "watched")
            db_session.commit()
            flash('History cleared', 'success')
            return redirect('/')
        else:
            flash('History NOT cleared', 'error')
            return redirect(url_for('user.history'))
    return render_template('widgets/widgets_confirm.html', message=message)


