from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func
from sqlalchemy import desc
from .database import db_session
from .models import Mv_Video, Mv_Category, Mv_Channel, Language
from .pagination import Pagination

bp = Blueprint('category', __name__, url_prefix='/category' )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
    offset = ((int(page)-1) * PER_PAGE)
    categorycount = db_session.query(func.count(Mv_Category.cat_id)).scalar()
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    categories = Mv_Category.query.limit(PER_PAGE).offset(offset)
    if not categories and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, categorycount)

    languages = Language.query.limit(PER_PAGE).offset(offset)

    return render_template('category/category_index.html', 
        pagination=pagination, videocount=videocount, categories=categories, categorycount=categorycount,
        locale=session['locale'])


@bp.route('/<cat_id>', defaults={'page': 1})
@bp.route('/<cat_id>/page/<int:page>')
def item(cat_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    category = Mv_Category.query.get(cat_id)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order,
        locale=session['locale'])


@bp.route('/<cat_id>/new', defaults={'page': 1})
@bp.route('/<cat_id>/new/page/<int:page>')
def item_new(cat_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'
    category = Mv_Category.query.get(cat_id)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.published.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order,
        locale=session['locale'])


@bp.route('/<cat_id>/old', defaults={'page': 1})
@bp.route('/<cat_id>/old/page/<int:page>')
def item_old(cat_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'oldest'
    category = Mv_Category.query.get(cat_id)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.published.asc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order,
        locale=session['locale'])


@bp.route('/<cat_id>/popular', defaults={'page': 1})
@bp.route('/<cat_id>/popular/page/<int:page>')
def item_popular(cat_id,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'
    category = Mv_Category.query.get(cat_id)
    cat_name = category.cat_name
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter_by(category=cat_name).scalar()
    videos = Mv_Video.query.filter_by(category=cat_name).order_by(Mv_Video.yt_views.desc()).limit(PER_PAGE).offset(offset)
    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('category/category_item.html', 
        pagination=pagination, category=category, videos=videos, videocount=videocount, order=order,
        locale=session['locale'])


@bp.route('/<lang_code>', defaults={'page': 1})
@bp.route('/<lang_code>/page/<int:page>')
def lang_item(lang_code,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'
    language = Language.query.get(lang_code)
    lang_tagstring = language.lang_tagstring

    search = lang_tagstring

    my_to_tsquery_video = text("mv_video.document @@ to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(my_ts_rank_video).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()


    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)  

    videos = Mv_Video.query.filter_by(category=cat_name).limit(PER_PAGE).offset(offset)

    if not videos and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, videocount)    
    return render_template('category/category_item.html', 
        pagination=pagination, language=language, videos=videos, videocount=videocount, order=order,
        locale=session['locale'])