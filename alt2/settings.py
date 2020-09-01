from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel
from .util import get_navtabs 

bp = Blueprint('settings', __name__, url_prefix='/settings' )

@bp.route('/', methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		session['locale'] = request.form['locale']
		session['theme'] = request.form['theme']
	videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
	delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()

	languages = (current_app.config['SUPPORTED_LANGUAGES'].keys())
	languages_list=list(languages)
	languages_list.remove(session['locale'])
	languages = languages_list

	themes = (current_app.config['SUPPORTED_THEMES'])
	themes_list=list(themes)
	if session.get('theme') is None:
		session['theme'] = 'light'
	themes_list.remove(session['theme'])
	themes = themes_list

	navtab_values = (current_app.config['SUPPORTED_NAVTABS'].values())
	navtab_tab1_values_list=list(navtab_values)

#	if session.get('navtabs') is None:
#		get_navtabs()


#	navtab_tab1_values_list.remove(session.get('navtabs'["tab1"]))
#	navtab_tab1_values = navtab_tab1_values_list

#	return render_template('settings/settings_index.html', videocount=videocount, \
#		delchannelcount=delchannelcount,languages=languages,themes=themes,navtab_tab1_values=navtab_tab1_values)

	return render_template('settings/settings_index.html', videocount=videocount, \
		delchannelcount=delchannelcount,languages=languages,themes=themes)