from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func
from flask_babelplus import Babel, gettext

from .database import db_session
from .models import Entity, Source, Mv_Video, Mv_Channel, Translation
from .util import get_locale, get_theme, get_navtabs, get_navtabs_index, get_navtabs_perm

bp = Blueprint('settings', __name__, url_prefix='/settings' )

@bp.route('/', methods=['GET', 'POST'])
def index():

    if session.get('locale') is None:
        get_locale()

    if session.get('theme') is None:
        session['theme'] = get_theme()

    if session.get('navtabs') is None:
        get_navtabs()

    if session.get('navtabs_index') is None:
        get_navtabs_index()

    if request.method == 'POST':

        fnt1 = request.form['navtab1_value']
        fnt2 = request.form['navtab2_value']
        fnt3 = request.form['navtab3_value']

        session['theme'] = request.form['theme']

        if session['locale'] != request.form['locale']:
            
            row = db_session.query(Translation).with_entities(getattr(Translation, session['locale']),getattr(Translation, request.form['locale'])).all()
            rowtuple = tuple(row)
            navtabs_change_locale = dict(rowtuple)

            fnt1 = navtabs_change_locale[fnt1]
            fnt2 = navtabs_change_locale[fnt2]
            fnt3 = navtabs_change_locale[fnt3]

        session['locale'] = request.form['locale']

        row = db_session.query(Translation).with_entities(getattr(Translation, session['locale']),Translation.en).all()
        rowtuple = tuple(row)
        navtabs_build_index = dict(rowtuple)

        session['navtabs_index']['navtab1'] = navtabs_build_index[fnt1]
        session['navtabs_index']['navtab2'] = navtabs_build_index[fnt2]
        session['navtabs_index']['navtab3'] = navtabs_build_index[fnt3]

        session['navtabs']['navtab1'] = fnt1
        session['navtabs']['navtab2'] = fnt2
        session['navtabs']['navtab3'] = fnt3
  
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()

    languages = (current_app.config['SUPPORTED_LANGUAGES'].keys())
    languages=list(languages)
    languages.remove(session['locale'])

    themes = (current_app.config['SUPPORTED_THEMES'])
    themes=list(themes)
    themes.remove(session['theme'])

    navtab_values = db_session.query(Translation).with_entities(getattr(Translation, session['locale'])).all()
    navtab_values = [r[0] for r in navtab_values]

    navtab1_values=list(navtab_values)
    navtab2_values=list(navtab_values)
    navtab3_values=list(navtab_values)

    navtab1_values.remove(session['navtabs']['navtab1'])
    navtab2_values.remove(session['navtabs']['navtab2'])
    navtab3_values.remove(session['navtabs']['navtab3'])

    return render_template('settings/settings_index.html', videocount=videocount, \
        delchannelcount=delchannelcount,languages=languages,themes=themes, \
        navtab1_values=navtab1_values, navtab2_values=navtab2_values, navtab3_values=navtab3_values)
