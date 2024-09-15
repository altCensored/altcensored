from flask import (Blueprint, render_template, flash)
from markupsafe import Markup
from .models import Mv_Channel
from .util import get_archivechannelcount
from . import config

bp = Blueprint('about', __name__, url_prefix='/about' )
FLASH_MSG = config.FLASH_MSG


@bp.route('/')
def index():
#    archchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    archivechannelcount = get_archivechannelcount()
    channels = Mv_Channel.query.all()

    if FLASH_MSG is not None:
        flash(Markup(FLASH_MSG), 'error')

    return render_template('about/about_index.html', channels=channels, archchancount=archivechannelcount)

@bp.route('/example')
def example():
    return render_template('video/video_overtest.html')