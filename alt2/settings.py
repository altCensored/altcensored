from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func
from flask_babelplus import Babel, gettext

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel, Translation
from .util import get_locale, get_theme, get_navtabs

bp = Blueprint('settings', __name__, url_prefix='/settings' )

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['locale'] = request.form['locale']
        session['theme'] = request.form['theme']

        session['navtabs']['navtab1'] = request.form['navtab1_value']
        session['navtabs']['navtab2'] = request.form['navtab2_value']
        session['navtabs']['navtab3'] = request.form['navtab3_value']
        
        
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
    navtab1_values=list(navtab_values)
    navtab2_values=list(navtab_values)
    navtab3_values=list(navtab_values)

    if session.get('navtabs') is None:
        get_navtabs()

    navtab1_values.remove(session['navtabs']['navtab1'])
    navtab2_values.remove(session['navtabs']['navtab2'])
    navtab3_values.remove(session['navtabs']['navtab3'])

#    row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
#    rowtuple = tuple(row)
#    navtabs = dict(rowtuple)

#    flash( navtabs, 'success')

#    session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys())
    row = db_session.query(Translation).with_entities(Translation.varname,getattr(Translation, session['locale'])).all()
    rowtuple = tuple(row)
    newnavtabs = dict(rowtuple)

#    flash( session['navtabs'], 'success')

    return render_template('settings/settings_index.html', videocount=videocount, \
        delchannelcount=delchannelcount,languages=languages,themes=themes, \
        navtab1_values=navtab1_values, navtab2_values=navtab2_values, navtab3_values=navtab3_values)
