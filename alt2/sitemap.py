from flask import Blueprint, Response, render_template
from .cache import cache
from .database import db_session
from .models import Mv_Video, Mv_Channel, Mv_Category
import math

bp = Blueprint('sitemap', __name__)

VIDEOS_PER_SITEMAP = 50000

@bp.route('/sitemap.xml')
def sitemap_index():
    video_count = db_session.query(Mv_Video).count()
    num_video_sitemaps = math.ceil(video_count / VIDEOS_PER_SITEMAP)
    xml = render_template('sitemap/sitemap_index.xml',
                          num_video_sitemaps=num_video_sitemaps)
    return Response(xml, mimetype='application/xml')

@bp.route('/sitemap-videos-<int:page>.xml')
def sitemap_videos(page):
    cache_key = f'sitemap_videos_{page}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, mimetype='application/xml')
    offset = (page - 1) * VIDEOS_PER_SITEMAP
    videos = db_session.query(Mv_Video.extractor_data, Mv_Video.published)\
        .order_by(Mv_Video.id)\
        .limit(VIDEOS_PER_SITEMAP)\
        .offset(offset)\
        .all()
    xml = render_template('sitemap/sitemap_videos.xml', videos=videos)
    cache.set(cache_key, xml, timeout=86400)
    return Response(xml, mimetype='application/xml')

@bp.route('/sitemap-channels.xml')
def sitemap_channels():
    cache_key = 'sitemap_channels'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, mimetype='application/xml')
    channels = db_session.query(Mv_Channel.ytc_id)\
        .order_by(Mv_Channel.ytc_id)\
        .all()
    xml = render_template('sitemap/sitemap_channels.xml', channels=channels)
    cache.set(cache_key, xml, timeout=86400)
    return Response(xml, mimetype='application/xml')

@bp.route('/sitemap-static.xml')
def sitemap_static():
    cache_key = 'sitemap_static'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, mimetype='application/xml')
    categories = Mv_Category.query.all()
    xml = render_template('sitemap/sitemap_static.xml', categories=categories)
    cache.set(cache_key, xml, timeout=86400)
    return Response(xml, mimetype='application/xml')