import datetime
from flask import Blueprint, render_template, session, request, abort
from sqlalchemy import func, select, and_, or_
from .database import db_session
from .models import Mv_Video, Mv_Category, Language, User
from .pagination import Pagination, CursorPagination
from .util import set_session, decode_cursor, encode_cursor, _exec_keyset

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


@bp.route('/<cat_id>')
def item(cat_id):
    if not cat_id.isdigit():
        abort(404)
    after_str = request.args.get('after') or None
    page = int(request.args.get('p', 1))
    order = 'latest'
    category = Mv_Category.query.get(cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    cursor = decode_cursor(after_str)
    stmt = select(Mv_Video).filter(Mv_Video.category == cat_name).order_by(Mv_Video.id.desc())
    if cursor:
        stmt = stmt.where(Mv_Video.id < cursor['id'])
    videos, has_next = _exec_keyset(stmt, PER_PAGE)
    if not videos and after_str:
        abort(404)
    next_cursor = encode_cursor({'id': videos[-1].id}) if has_next else None
    pagination = CursorPagination(has_next, next_cursor, page)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html',
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order, watchlater=watchlater)


@bp.route('/<cat_id>/new')
def item_new(cat_id):
    if not cat_id.isdigit():
        abort(404)
    after_str = request.args.get('after') or None
    page = int(request.args.get('p', 1))
    order = 'newest'
    category = Mv_Category.query.get(cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    cursor = decode_cursor(after_str)
    stmt = (
        select(Mv_Video)
        .filter(Mv_Video.category == cat_name)
        .order_by(Mv_Video.published.desc(), Mv_Video.extractor_data.desc())
    )
    if cursor:
        v_raw = cursor.get('pub')
        t = cursor['eid']
        if v_raw is None:
            stmt = stmt.where(and_(Mv_Video.published.is_(None), Mv_Video.extractor_data < t))
        else:
            v = datetime.datetime.fromisoformat(v_raw)
            stmt = stmt.where(or_(
                Mv_Video.published < v,
                and_(Mv_Video.published == v, Mv_Video.extractor_data < t),
                Mv_Video.published.is_(None),
            ))
    videos, has_next = _exec_keyset(stmt, PER_PAGE)
    if not videos and after_str:
        abort(404)
    next_cursor = encode_cursor({'pub': videos[-1].published, 'eid': videos[-1].extractor_data}) if has_next else None
    pagination = CursorPagination(has_next, next_cursor, page)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html',
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order, watchlater=watchlater)


@bp.route('/<cat_id>/popular')
def item_popular(cat_id):
    if not cat_id.isdigit():
        abort(404)
    after_str = request.args.get('after') or None
    page = int(request.args.get('p', 1))
    order = 'popular'
    category = Mv_Category.query.get(cat_id)
    if category is None:
        abort(404)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    cursor = decode_cursor(after_str)
    stmt = (
        select(Mv_Video)
        .filter(Mv_Video.category == cat_name)
        .order_by(Mv_Video.yt_views.desc(), Mv_Video.extractor_data.desc())
    )
    if cursor:
        v_raw = cursor.get('views')
        t = cursor['eid']
        if v_raw is None:
            stmt = stmt.where(and_(Mv_Video.yt_views.is_(None), Mv_Video.extractor_data < t))
        else:
            stmt = stmt.where(or_(
                Mv_Video.yt_views < v_raw,
                and_(Mv_Video.yt_views == v_raw, Mv_Video.extractor_data < t),
                Mv_Video.yt_views.is_(None),
            ))
    videos, has_next = _exec_keyset(stmt, PER_PAGE)
    if not videos and after_str:
        abort(404)
    next_cursor = encode_cursor({'views': videos[-1].yt_views, 'eid': videos[-1].extractor_data}) if has_next else None
    pagination = CursorPagination(has_next, next_cursor, page)
    watchlater = None
    if session.get('user') is not None:
        user = User.query.filter(User.id == session['user']['id']).scalar()
        if user.watchlater:
            watchlater = user.watchlater

    return render_template('category/category_item.html',
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order, watchlater=watchlater)