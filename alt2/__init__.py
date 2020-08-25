import os, time, re
from flask import Flask, send_from_directory, request, url_for, redirect, g, flash, session

from flask_seasurf import SeaSurf
from flask_talisman import Talisman
from jinja2 import evalcontextfilter, Markup, escape
from flask_babelplus import Babel, gettext, ngettext

import bleach
import unicodedata
import math
from . import util

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='', instance_relative_config=True)

    app.config.from_pyfile(os.path.join(app.root_path, 'config.py'),silent=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY=app.config['SECRET_KEY'],
        DATABASE=os.path.join(app.instance_path, 'altcen.db'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    babel = Babel(app)

    # Flask-BabelPlus
    babel.init_app(app=app)

    @babel.localeselector
    def get_locale():
        return util.get_locale()

    @babel.timezoneselector
    def get_timezone():
        user = getattr(g, 'user', None)
        if user is not None:
            return user.timezone 


    @app.template_filter('viewdisplay')
    def viewdisplay(views):
        if views < 1000:
            return views
        elif (views >= 1000) and (views < 10000):
            return str(math.floor((views / 1000)*10)/10) + 'K'

        elif (views >= 10000) and (views < 1000000):
            return str(views // 1000) + 'K'

        elif (views >= 1000000) and (views < 10000000):
            return str(math.floor((views / 1000000)*10)/10) + 'M'

        elif (views >= 10000000) and (views < 1000000000):
            return str(views // 1000000) + 'M'

        elif (views >= 1000000000) and (views < 10000000000):
            return str(math.floor((views / 1000000000)*10)/10) + 'B'

        elif (views >= 10000000000) and (views < 1000000000000):
            return str(views // 1000000000) + 'B'


    @app.template_filter('commafy')
    def commafy(value):
        return "{:,}".format(value)

    @app.template_filter('spaceplus')
    def spaceplus(value):
        return value.replace(' ', '+')
#        return "{:+}".format(value)

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%Y'):
        return value.strftime(format)

    @app.template_filter('hourminsec')
    def secs_to_HMS2(secs):
        if secs < 3600:
            return time.strftime('%-M:%S', time.gmtime(secs))
        else:
            return time.strftime('%-H:%M:%S', time.gmtime(secs))
 
    @app.template_filter('ia_fname')
    def ia_fname(video_title):
        video_title = video_title.replace(':',' -').replace("’",'_')
        video_title = unicodedata.normalize('NFD', video_title).encode('Windows-1252','ignore')
        video_title = re.sub('[^A-Za-z0-9-.+~=%@]+', '_', video_title.decode('Windows-1252') )
        video_title = video_title.rstrip('_').lstrip('_')
        return video_title

    @app.template_filter('linkify')
    def linkify(s):
        return bleach.linkify(s)

    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

    @app.template_filter('nl2br')
    @evalcontextfilter
    def nl2br(eval_ctx, value):
        result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                              for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

    @app.context_processor
    def inject_locale_and_theme():
        return dict(locale=util.get_locale(), theme=util.get_theme())

    def has_no_empty_params(rule):
        defaults = rule.defaults if rule.defaults is not None else ()
        arguments = rule.arguments if rule.arguments is not None else ()
        return len(defaults) >= len(arguments)

    def page_not_found(e):
        return redirect(url_for('video.index'))

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(400, page_not_found)
    app.register_error_handler(500, page_not_found)



#
# http://flask.pocoo.org/docs/1.0/patterns/sqlalchemy/
#
    from .database import db_session

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()    

    # apply the blueprints to the app
    from . import video, channel, about, category, language, settings, auth, theme
    app.register_blueprint(video.bp)
    app.register_blueprint(channel.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(category.bp)
    app.register_blueprint(language.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(theme.bp)
    # app.register_blueprint(auth.bp)
    # make url_for('index') == url_for('blog.index')
    # in another app, you might define a separate main index here with
    # app.route, while giving the blog blueprint a url_prefix, but for
    # the tutorial the blog will be the main index
    app.add_url_rule('/', endpoint='video.index', defaults={'page': 1})




#    csrf = SeaSurf(app)

    csp = {
#        'default-src': '\'self\'',
        'img-src': [
            'data:',
            '\'self\'',
            '*',
    ],
        'worker-src': [
            'unsafe-inline',
            '\'self\'',
            'blob:',
#    ],           
#        'script-src': [
#            'unsafe-inline',
#            '\'self\'',
    ]
    }



    feature_policy = {
        'geolocation': '\'none\''
    }

    talisman = Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        feature_policy=feature_policy,
        frame_options='ALLOW_FROM',
        frame_options_allow_from='*'
    )


#    @app.route('/favicon.ico')
#    def favicon():
#        return send_from_directory(os.path.join(app.root_path, 'static'),
#                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
        
    def url_for_other_page(page):
        args = request.view_args.copy()
        args['page'] = page
        return url_for(request.endpoint, **args)


    app.jinja_env.globals['url_for_other_page'] = url_for_other_page


    return app
