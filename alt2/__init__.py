import os, re, logging
from flask import Flask, request, url_for, render_template, g, has_request_context
from jinja2 import pass_eval_context
from flask_babelplus import Babel, lazy_gettext
from urllib.parse import quote_plus
from flask_qrcode import QRcode
from markupsafe import escape, Markup
import timeago, datetime
from datetime import timezone
import bleach
import unicodedata
import math
from . import util
from .cache import cache
from psycogreen.gevent import patch_psycopg
from flask_talisman import Talisman

#import sentry_sdk
#from sentry_sdk.integrations.flask import FlaskIntegration


#sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'),
##                debug=True,
#                send_default_pii=True,
#                traces_sample_rate=1.0,
#                integrations=[FlaskIntegration()])

patch_psycopg()

csp = {
    'default-src': [
        '\'self\'',
        'altcensored.com',
        '*.altcensored.com'
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\''
    ],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        '*.altcensored.com'
    ],
    'media-src': [
        '\'self\'',
        '*.altcensored.com',
        'archive.org',
        '*.archive.org'
    ],
    'img-src': [
        '*',
        'data:'
    ],
    'font-src': [
        '\'self\'',
        'data:'
    ],
    'frame-src': [
        '*'
    ],
    'frame-ancestors': [
        '*',
        'data:'
    ]
}

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='', instance_relative_config=True)

    app.config.from_pyfile(os.path.join(app.root_path, 'config.py'),silent=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY=app.config['SECRET_KEY'],
        DATABASE=os.path.join(app.instance_path, 'altcen.db'),
        PROPAGATE_EXCEPTIONS=app.config['PROPAGATE_EXCEPTIONS'],
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

    if __name__ != '__main__':
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    babel = Babel(app)
    QRcode(app)
    cache.init_app(app)
    Talisman(app, content_security_policy=csp)


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
        if views is None:
            return 0
        elif views < 1000:
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
        if value is None:
            return 0
        else:
            return "{:,}".format(value)

    @app.template_filter('spaceplus')
    def spaceplus(value):
        return value.replace(' ', '+')

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%Y'):
        return value.strftime(format)

    @app.template_filter('hourminsec')
    def secs_to_HMS2(secs):
        if secs < 3600:
            m, s = divmod(secs, 60)
            h, m = divmod(m, 60)
            return ('{:0>2}:{:0>2}'.format(m, s)).lstrip("0")

        else:
            m, s = divmod(secs, 60)
            h, m = divmod(m, 60)
            return ('{}:{:0>2}:{:0>2}'.format(h, m, s)).lstrip("0")

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
    @pass_eval_context
    def nl2br(eval_ctx, value):
        result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                              for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

    @app.template_filter('bwremaining')
    def bwremaining(bwlimit, bwused):
        if bwlimit == 0:
           return lazy_gettext('Bandwidth Unlimited')
        else:
            bwremaining = bwlimit - bwused
            gb = 1.0 / 1024
            convert_gb = round(gb * bwremaining,2)
            return str(convert_gb) + ' GB Remaining'

    @app.context_processor
    def inject_context():
        return dict(
            locale=util.get_locale(),
            theme=util.get_theme(),
            playnext=util.get_playnext(),
            autoplay=util.get_autoplay(),
            looplist=util.get_looplist(),
            current_url=quote_plus(request.url),
            current_path=quote_plus(request.full_path),
            navtabs=util.get_navtabs(),
            navtabs_index=util.get_navtabs_index(),
            usercount=util.get_usercount(),
            videocount=util.get_videocount(),
            channelcount=util.get_channelcount(),
            delchannelcount=util.get_delchannelcount()
        )

#    @app.before_request
#    def before_req():
#        util.set_session()

    def has_no_empty_params(rule):
        defaults = rule.defaults if rule.defaults is not None else ()
        arguments = rule.arguments if rule.arguments is not None else ()
        return len(defaults) >= len(arguments)

    def bad_request(e):
#        app.logger.error(e)
        return render_template('video/400.html'), 400

    def page_not_found(e):
        if has_request_context():
            app.logger.error('404 Not Found: Requested URL: %s', request.url)
        else:
            app.logger.error(e)
        return render_template('video/404.html'), 404

    def internal_server_error(e):
        if has_request_context():
            app.logger.error('500 Internal Error: %s', request.url)
        else:
            app.logger.error(e)
        return render_template('video/500.html'), 500

    @app.template_filter('time_diff')
    def time_diff(s):
        now = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=60 * 3.4)
        return timeago.format(s, now)

    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    from .database import db_session

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()    

    from . import video, channel, about, category, language, settings, auth, admin, playlist, theme, user, newsletter, vpn, donate

    app.register_blueprint(video.bp)
    app.register_blueprint(channel.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(category.bp)
    app.register_blueprint(language.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(playlist.bp)
    app.register_blueprint(theme.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(newsletter.bp)
    app.register_blueprint(vpn.bp)
    app.register_blueprint(donate.bp)

    app.add_url_rule('/', endpoint='video.index', defaults={'page': 1})

    def url_for_other_page(page):
        args = request.view_args.copy()
        args['page'] = page
        return url_for(request.endpoint, **args)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page

    return app
