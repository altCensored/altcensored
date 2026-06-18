from flask import ( Blueprint, render_template, session, abort )
from sqlalchemy import func
from .database import db_session
from .models import Mv_Video, Mv_Category, Language, User
from .pagination import Pagination
from .util import set_session

bp = Blueprint('category', __name__, url_prefix='/category' )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
#    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    categorycount = db_session.query(func.count(Mv_Category.cat_id)).scalar()
    categories = Mv_Category.query.limit(PER_PAGE).offset(offset)
    if not categories and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, categorycount)

    languages = Language.query.limit(PER_PAGE).offset(offset)

    return render_template('category/category_index.html', 
        pagination=pagination, categories=categories, categorycount=categorycount)


@bp.route('/<cat_id>', defaults={'page': 1})
@bp.route('/<cat_id>/page/<int:page>')
def item(cat_id,page):
    if not cat_id.isdigit():
        abort(404)
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    category = db_session.get(Mv_Category, cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.id.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order, watchlater=watchlater)


@bp.route('/<cat_id>/new', defaults={'page': 1})
@bp.route('/<cat_id>/new/page/<int:page>')
def item_new(cat_id,page):
    if not cat_id.isdigit():
        abort(404)
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    category = db_session.get(Mv_Category, cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.published.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order)


@bp.route('/<cat_id>/popular', defaults={'page': 1})
@bp.route('/<cat_id>/popular/page/<int:page>')
def item_popular(cat_id,page):
    if not cat_id.isdigit():
        abort(404)
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    category = db_session.get(Mv_Category, cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html',
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order)