from flask import (Blueprint, render_template)
from .models import Mv_Channel
from .util import get_archivechannelcount

bp = Blueprint('about', __name__, url_prefix='/about' )

@bp.route('/')
def index():
#    archchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    archivechannelcount = get_archivechannelcount()
    channels = Mv_Channel.query.all()

    return render_template('about/about_index.html', channels=channels, archchancount=archivechannelcount)

@bp.route('/example')
def example():
    return render_template('video/video_overtest.html')