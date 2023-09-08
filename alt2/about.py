from flask import (Blueprint, render_template)
from sqlalchemy import func

from .database import db_session
from .models import Mv_Channel
from .cache import cache

bp = Blueprint('about', __name__, url_prefix='/about' )

@bp.route('/')
@cache.cached()
def index():
    archchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    channels = Mv_Channel.query.all()

    return render_template('about/about_index.html', channels=channels, archchancount=archchancount)

@bp.route('/example')
def example():
    return render_template('video/video_overtest.html')