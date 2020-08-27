from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    send_from_directory, make_response, session, current_app )
from sqlalchemy import func, text, case
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta

from . import util
from .models import Mv_Video, Mv_Channel, Mv_Category, User
from .database import db_session
from .pagination import Pagination
from .auth import login_required


bp = Blueprint('history', __name__, url_prefix='/history')

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
@login_required
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    user = db_session.query(User).filter(User.email == session['user']['email']).one()
    try:
        ordering = case(
            {id: index for index, id in reversed(list(enumerate(reversed(user.watched))))},
            value=Mv_Video.id
         )
        videos = Mv_Video.query.filter(Mv_Video.id.in_(user.watched)).order_by(ordering).limit(PER_PAGE).offset(offset)
        videocount = db_session.query(func.count(Mv_Video.id)).filter(Mv_Video.id.in_(user.watched)).scalar()
        pagination = Pagination(page, PER_PAGE, videocount)  
        return render_template('history/history_index.html', locale=util.get_locale(), pagination=pagination, videos=videos, videocount=videocount)
    except:
        flash('No History Available', 'success')
        return redirect('/')


@bp.route('/clear_watch_history', methods=['GET', 'POST'])
@login_required
def clear_watch_history():
    if request.method == 'POST':
        submitvalue = request.form['submitvalue']
        if submitvalue == 'yes':
            user = db_session.query(User).filter(User.email == session['user']['email']).one()
            user.watched = None
            flag_modified(user, "watched")
            db_session.commit()
            return redirect('/')
        else:
            return redirect('/')
    return render_template('/history/history_clear_watch.html')
