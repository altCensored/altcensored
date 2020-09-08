from flask import (
    Blueprint, session, render_template
)

from sqlalchemy import func
from .models import User
from .database import db_session
from .pagination import Pagination

bp = Blueprint('user', __name__, url_prefix='/user' )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    usercount = db_session.query(func.count(User.id)).scalar()
    users = User.query.limit(PER_PAGE).offset(offset)
    if not users and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, usercount)

    return render_template('user/user_index.html', 
        pagination=pagination, usercount=usercount, users=users)


@bp.route('/<user>')
def item(user):
    user = db_session.query(User).filter(func.lower(User.username) == func.lower(user)).scalar()
    if not user and page != 1:
        abort(404)
    return render_template('user/user_item.html', 
        user=user)