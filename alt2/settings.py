import datetime
from datetime import timezone

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, current_app, session
)
from sqlalchemy import func

from .database import db_session
from .models import Mv_Video, Mv_Channel, Translation, User, Playlist
from . import util
from .util import set_session

bp = Blueprint('settings', __name__, url_prefix='/settings')

def username_exists(username):
    if username == session['user']['username']:
        return False
    if db_session.query(User.username).filter(func.lower(User.username) == func.lower(username)).scalar() is not None:
        return True

@bp.route('/')
def index():
    set_session()
    return render_template('settings/settings_index.html')

@bp.route('/update_site', methods=['GET', 'POST'])
def update_site():
    set_session()
    if request.method == 'POST':
        fnt1 = request.form['navtab1_value']
        fnt2 = request.form['navtab2_value']
        fnt3 = request.form['navtab3_value']

        session['theme'] = request.form['theme']
        session['playnext'] = util.str_to_bool(request.form['playnext'])
        session['looplist'] = util.str_to_bool(request.form['looplist'])

        if session['locale'] != request.form['locale']:
            row = db_session.query(Translation).with_entities(getattr(Translation, session['locale']),
                                                              getattr(Translation, request.form['locale'])).all()
            rowtuple = tuple(row)
            navtabs_change_locale = dict(rowtuple)

            fnt1 = navtabs_change_locale[fnt1]
            fnt2 = navtabs_change_locale[fnt2]
            fnt3 = navtabs_change_locale[fnt3]

        session['locale'] = request.form['locale']

        row = db_session.query(Translation).with_entities(getattr(Translation, session['locale']), Translation.en).all()
        rowtuple = tuple(row)
        navtabs_build_index = dict(rowtuple)

        session['navtabs_index']['navtab1'] = navtabs_build_index[fnt1]
        session['navtabs_index']['navtab2'] = navtabs_build_index[fnt2]
        session['navtabs_index']['navtab3'] = navtabs_build_index[fnt3]

        session['navtabs']['navtab1'] = fnt1
        session['navtabs']['navtab2'] = fnt2
        session['navtabs']['navtab3'] = fnt3

        if 'user' in session:
            user = User.query.get(session['user']['id'])
            now = datetime.datetime.now(timezone.utc)
            user.updated = now
            user.settings = {
                "theme": session['theme'],
                "locale": session['locale'],
                "playnext": session['playnext'],
                "looplist": session['looplist']
            }
            user.navtabs = [session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3']]
            user.navtabs_index = [session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'],
                                  session['navtabs_index']['navtab3']]
            db_session.commit()

            return redirect(url_for('settings.index'))

    locales = (current_app.config['SUPPORTED_LANGUAGES'].keys())
    locales = list(locales)
    locales.remove(session['locale'])

    themes = (current_app.config['SUPPORTED_THEMES'])
    themes = list(themes)
    themes.remove(session['theme'])

    navtab_values = db_session.query(Translation).with_entities(getattr(Translation, session['locale'])).all()
    navtab_values = [r[0] for r in navtab_values]

    navtab1_values = list(navtab_values)
    navtab2_values = list(navtab_values)
    navtab3_values = list(navtab_values)

    navtab1_values.remove(session['navtabs']['navtab1'])
    navtab2_values.remove(session['navtabs']['navtab2'])
    navtab3_values.remove(session['navtabs']['navtab3'])

    return render_template('settings/settings_site.html', locales=locales, themes=themes,
                           navtab1_values=navtab1_values, navtab2_values=navtab2_values, navtab3_values=navtab3_values)


@bp.route('/update_user', methods=['GET', 'POST'])
@util.login_required
def update_user():
    if request.method == 'POST':
        fusername = request.form['username']
        fdescription = request.form['description']
        fpublic = util.str_to_bool(request.form['public'])
        ffeatured_playlist = request.form.get('featured_playlist')

        if util.contains_profanity(fusername):
            flash('Profanity not allowed', 'error')
            return redirect(url_for('settings.update_user'))
        if util.contains_profanity(fdescription):
            flash('Profanity not allowed', 'error')
            return redirect(url_for('settings.update_user'))

        session['user']['username'] = fusername
        session['user']['description'] = fdescription
        session['user']['public'] = fpublic
        session.modified = True

        user = User.query.get(session['user']['id'])
        playlist = Playlist.query.filter(Playlist.title == ffeatured_playlist).scalar()
        if playlist is not None and playlist.featured_video is not None:
            user.featured_playlist = playlist.featured_video

        now = datetime.datetime.now(timezone.utc)
        user.updated = now
        user.username = fusername
        user.description = fdescription
        user.public = fpublic

        db_session.commit()

        return redirect(url_for('settings.index'))

    playlist_titles = db_session.query(Playlist).with_entities(getattr(Playlist, "title")) \
        .filter((Playlist.public), (Playlist.user_id == session['user']['id'])).all()
    playlist_titles = [r[0] for r in playlist_titles]
    playlist_titles = list(playlist_titles)

    user = User.query.get(session['user']['id'])
    featured_playlist = None

#    if user.featured_playlist is not None:
#        featured_playlist = Playlist.query.filter(Playlist.title == user.featured_playlist.pl_title).scalar()
#        try:
#            playlist_titles.remove(featured_playlist.title)
#        except:
#            pass

    return render_template('settings/settings_user_update.html', playlist_titles=playlist_titles, featured_playlist=featured_playlist)