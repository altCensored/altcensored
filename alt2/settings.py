from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel

bp = Blueprint('settings', __name__, url_prefix='/settings' )

@bp.route('/', methods=['GET', 'POST'])
def index():

	if request.method == 'POST':
		locale = request.form['locale']
		session['locale'] = request.form['locale']
	videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
	delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()
	languages = (current_app.config['SUPPORTED_LANGUAGES'].keys())
	locale = session['locale']
	languages_list=list(languages)
	languages_list.remove(locale)
	languages = languages_list

	return render_template('settings/settings_index.html', videocount=videocount, \
		delchannelcount=delchannelcount,languages=languages,locale=locale)
