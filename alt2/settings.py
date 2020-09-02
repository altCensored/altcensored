from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func
from flask_babelplus import Babel, gettext

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel
from .util import get_locale, get_theme, get_navtabs

bp = Blueprint('settings', __name__, url_prefix='/settings' )

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['locale'] = request.form['locale']
        session['theme'] = request.form['theme']

 #       session['navtabs']['tab1'] = request.form['tab1_value']
 #       session['navtabs']['tab2'] = request.form['tab2_value']
 #       session['navtabs']['tab3'] = request.form['tab3_value']
        
        navkey1 = (list(session['navtabs'].keys())[list(session['navtabs'].values()).index(request.form['tab1_value'])])
        navkey2 = (list(session['navtabs'].keys())[list(session['navtabs'].values()).index(request.form['tab2_value'])])
        navkey3 = (list(session['navtabs'].keys())[list(session['navtabs'].values()).index(request.form['tab3_value'])])

        session['act_navtabs'].clear()
        session['act_navtabs'][navkey1] = request.form['tab1_value']
        session['act_navtabs'][navkey2] = request.form['tab2_value']
        session['act_navtabs'][navkey3] = request.form['tab3_value']

        session['tmp_navtabs'].clear()
        session['tmp_navtabs']['tab1'] = request.form['tab1_value']
        session['tmp_navtabs']['tab2'] = request.form['tab2_value']
        session['tmp_navtabs']['tab3'] = request.form['tab3_value']
        
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()

    languages = (current_app.config['SUPPORTED_LANGUAGES'].keys())
    languages_list=list(languages)
    if session.get('locale') is None:
        get_locale()    
    languages_list.remove(session['locale'])
    languages = languages_list

    themes = (current_app.config['SUPPORTED_THEMES'])
    themes_list=list(themes)
    if session.get('theme') is None:
        session['theme'] = get_theme()
    themes_list.remove(session['theme'])
    themes = themes_list

    navtab_values = (current_app.config['SUPPORTED_NAVTABS'].values())
    tab1_values=list(navtab_values)
    tab2_values=list(navtab_values)
    tab3_values=list(navtab_values)

    if session.get('navtabs') is None:
        get_navtabs()

    if session.get('act_navtabs') is None:
        get_act_navtabs() 

    if session.get('tmp_navtabs') is None:
        get_tmp_navtabs() 

    tab1_values.remove(session['tmp_navtabs']['tab1'])
    tab2_values.remove(session['tmp_navtabs']['tab2'])
    tab3_values.remove(session['tmp_navtabs']['tab3'])

    return render_template('settings/settings_index.html', videocount=videocount, \
        delchannelcount=delchannelcount,languages=languages,themes=themes, \
        tab1_values=tab1_values, tab2_values=tab2_values, tab3_values=tab3_values)
