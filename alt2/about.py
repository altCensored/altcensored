from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel
from . import util


bp = Blueprint('about', __name__, url_prefix='/about' )


@bp.route('/')
def index():
    """Show all the posts, newest first."""

#    channelcount = db_session.query(Mv_Channel.id).count()
    channelcount = db_session.query(func.count(Mv_Channel.ytc_id)).scalar()

#    videocount = db_session.query(Mv_Video.id).count()
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()

#    delchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleteddate!='2001-01-01').scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
    archchancount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_archive).scalar()
    channels = Mv_Channel.query.all()

    return render_template('about/about_index.html' , channels=channels, channelcount=channelcount, videocount=videocount, archchancount=archchancount, delchannelcount=delchannelcount, locale=util.get_locale())


