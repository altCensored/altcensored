from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, g, current_app, session
    )
from werkzeug.exceptions import abort
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from flask_babelplus import Babel, gettext
import datetime
from datetime import timezone

from .database import db_session
from .models import Mv_Video, Mv_Channel, Translation, User
from .util import get_locale, get_theme, get_navtabs, get_navtabs_index, get_navtabs_perm, str_to_bool, contains_profanity

bp = Blueprint('settings', __name__, url_prefix='/settings' )

def username_exists(username):
    if username == session['user']['username']:
        return False
    if db_session.query(User.username).filter(func.lower(User.username) == func.lower(username)).scalar() is not None:
        return True

@bp.route('/')
def index():
    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()

    return render_template('settings/settings_index.html', videocount=videocount, delchannelcount=delchannelcount)


@bp.route('/site', methods=['GET', 'POST'])
def site():
    if session.get('locale') is None:
        get_locale()
    if session.get('theme') is None:
        session['theme'] = get_theme()
    if session.get('playnext') is None:
        get_playnext()
    if session.get('looplist') is None:
        get_looplist()
    if session.get('navtabs') is None:
        get_navtabs()
    if session.get('navtabs_index') is None:
        get_navtabs_index()
    if request.method == 'POST':
        fnt1 = request.form['navtab1_value']
        fnt2 = request.form['navtab2_value']
        fnt3 = request.form['navtab3_value']

        session['playnext'] = str_to_bool(request.form['playnext'])
        session['looplist'] = str_to_bool(request.form['looplist'])
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
  
        if 'user' in session:
            fusername = request.form['username']
            fdescription = request.form['description']
            fpublic = str_to_bool(request.form['public'])

            if contains_profanity(fusername):
                flash('Profanity not allowed', 'error')
                return redirect(url_for('settings.index'))
            if contains_profanity(fdescription):
                flash('Profanity not allowed', 'error')
                return redirect(url_for('settings.index'))
 
            session['user']['username'] = fusername
            session['user']['description'] = fdescription
            session['user']['public'] = fpublic

            now = datetime.datetime.now(timezone.utc)
            user = db_session.query(User).filter(User.email == session['user']['email']).one()
            user.updated = now
            user.settings = {
            "theme": session['theme'],
            "locale": session['locale'],
            "playnext": session['playnext']
            }

            user.username = fusername
            user.description = fdescription
            user.public = fpublic
            user.navtabs =  [ session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3'] ]
            user.navtabs_index =  [ session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3'] ]
            db_session.commit()

            return redirect(request.args.get('original_url', '/'))

    videocount = db_session.query(func.count(Mv_Video.extractor_data)).scalar()
    delchannelcount = db_session.query(func.count(Mv_Channel.ytc_id)).filter(Mv_Channel.ytc_deleted).scalar()

    locales = (current_app.config['SUPPORTED_LANGUAGES'].keys())
    locales=list(locales)
    locales.remove(session['locale'])

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

    return render_template('settings/settings_site.html', videocount=videocount, \
        delchannelcount=delchannelcount, locales=locales, themes=themes, \
        navtab1_values=navtab1_values, navtab2_values=navtab2_values, navtab3_values=navtab3_values)