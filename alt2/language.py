from flask import ( Blueprint, render_template, abort )
from sqlalchemy import func, text
from .database import db_session
from .models import Mv_Video, Mv_Channel, Language
from .pagination import Pagination
from . import util
from .util import set_session

bp = Blueprint('language', __name__, url_prefix='/language' )

PER_PAGE = 24

@bp.route('/', defaults={'page': 1})
@bp.route('/page/<int:page>')
def index(page):
#    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    languagecount = db_session.query(func.count(Language.lang_id)).scalar()
    languages = Language.query.limit(PER_PAGE).offset(offset)
    if not languages and page != 1:
        abort(404)
    pagination = Pagination(page, PER_PAGE, languagecount)

    return render_template('language/language_index.html', pagination=pagination, languages=languages, languagecount=languagecount, locale=util.get_locale())


@bp.route('/<lang_code>', defaults={'page': 1})
@bp.route('/<lang_code>/page/<int:page>')
def item(lang_code,page):
#    set_session()
    offset = ((int(page)-1) * PER_PAGE)
    order = 'latest'

    language = Language.query.filter_by(lang_code=lang_code).first()
    rawsearch = language.lang_tagstring
    rawsearch_str = ''.join(rawsearch)
    search = rawsearch.replace(',','|')

    my_to_tsquery_video = text("mv_video.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, websearch_to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.id.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, websearch_to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        order_by(my_ts_rank_channel).\
        limit(48).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('language/language_index.html', videos=videos)
    else:
        return render_template('language/language_item.html',videos=videos,pagination=pagination,order=order,channels=channels,videocount=videocount,channelcount=channelcount,language=language)


@bp.route('/<lang_code>/new', defaults={'page': 1})
@bp.route('/<lang_code>/new/page/<int:page>')
def item_new(lang_code,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'newest'

    language = Language.query.filter_by(lang_code=lang_code).first()
    rawsearch = language.lang_tagstring
    rawsearch_str = ''.join(rawsearch)
    search = rawsearch.replace(',','|')

    my_to_tsquery_video = text("mv_video.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, websearch_to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.published.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, websearch_to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        order_by(my_ts_rank_channel).\
        limit(48).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('language/language_index.html', videos=videos)
    else:
        return render_template('language/language_item.html',videos=videos,pagination=pagination,order=order,channels=channels,videocount=videocount,channelcount=channelcount,language=language)


@bp.route('/<lang_code>/old', defaults={'page': 1})
@bp.route('/<lang_code>/old/page/<int:page>')
def item_old(lang_code,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'oldest'

    language = Language.query.filter_by(lang_code=lang_code).first()
    rawsearch = language.lang_tagstring
    rawsearch_str = ''.join(rawsearch)
    search = rawsearch.replace(',','|')

    my_to_tsquery_video = text("mv_video.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, websearch_to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.published.asc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, websearch_to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        order_by(my_ts_rank_channel).\
        limit(48).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('language/language_index.html', videos=videos)
    else:
        return render_template('language/language_item.html',videos=videos,pagination=pagination,order=order,channels=channels,videocount=videocount,channelcount=channelcount,language=language)


@bp.route('/<lang_code>/popular', defaults={'page': 1})
@bp.route('/<lang_code>/popular/page/<int:page>')
def item_popular(lang_code,page):
    offset = ((int(page)-1) * PER_PAGE)
    order = 'popular'

    language = Language.query.filter_by(lang_code=lang_code).first()
    rawsearch = language.lang_tagstring
    rawsearch_str = ''.join(rawsearch)
    search = rawsearch.replace(',','|')

    my_to_tsquery_video = text("mv_video.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_video = text("ts_rank(mv_video.document, websearch_to_tsquery(:search)) DESC")
    videos = db_session.query(Mv_Video).\
        filter(my_to_tsquery_video).\
        order_by(Mv_Video.yt_views.desc()).\
        limit(PER_PAGE).offset(offset).\
        params(search=search).all()

    my_to_tsquery_channel = text("Mv_Channel.document @@ websearch_to_tsquery(:search)")
    my_ts_rank_channel = text("ts_rank(Mv_Channel.document, websearch_to_tsquery(:search)) DESC")
    channels = db_session.query(Mv_Channel).\
        filter(my_to_tsquery_channel).\
        order_by(my_ts_rank_channel).\
        limit(48).\
        params(search=search).all()

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).filter(my_to_tsquery_video).params(search=search).scalar()
    channelcount = db_session.query(func.count(Mv_Channel.id)).filter(my_to_tsquery_channel).params(search=search).scalar()
    pagination = Pagination(page, PER_PAGE, videocount)   

    if videos is None:
        videos = Mv_Video.query.limit(24).all()
        return render_template('language/language_index.html', videos=videos)
    else:
        return render_template('language/language_item.html',videos=videos,pagination=pagination,order=order,channels=channels,videocount=videocount,channelcount=channelcount,language=language)
