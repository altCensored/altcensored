from flask import (Blueprint, render_template)
from sqlalchemy import func

from .database import db_session
from .models import Mv_Channel
from .util import set_session

bp = Blueprint('about', __name__, url_prefix='/about' )

@bp.route('/')
def index():
#    set_session()
    archchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    channels = Mv_Channel.query.all()

    return render_template('about/about_index.html', channels=channels, archchancount=archchancount)


