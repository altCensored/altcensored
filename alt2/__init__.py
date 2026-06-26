import os, re, logging
import urllib3
from minio import Minio
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request, url_for, render_template, g, has_request_context, flash, redirect
from jinja2 import pass_eval_context
from flask_babelplus import Babel, lazy_gettext as _l
from flask_mail import Mail
from urllib.parse import quote_plus
from flask_qrcode import QRcode
from flask_wtf.csrf import CSRFProtect
from markupsafe import escape, Markup
import timeago, datetime
from datetime import timezone
import bleach
import nh3
import unicodedata
import math
from . import util
from .cache import cache
from .database import db_session
from psycogreen.gevent import patch_psycopg
from flask_talisman import Talisman

csrf = CSRFProtect()

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
        '*.cloudflare.com',
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
        '\'self\'',
        'altcensored.com',
        '*.altcensored.com',
        'archive.org',
        '*.archive.org',
    ],
    'frame-ancestors': [
        '\'self\'',
        'altcensored.com',
        '*.altcensored.com',
    ]
}

mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

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
    Talisman(app, content_security_policy=csp, content_security_policy_nonce_in=['script-src'])
    mail.init_app(app)
    csrf.init_app(app)  # ← add this line
    limiter.init_app(app)

    try:
        app.minio_client = Minio(
            app.config['AC_S3_ENDPOINT'],
            access_key=app.config['AC_S3_ACCESS_KEY'],
            secret_key=app.config['AC_S3_SECRET_KEY'],
            http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=2.0, read=2.0)),
        )
    except Exception:
        app.minio_client = None
        app.logger.warning("Minio client init failed — S3 videos will be unavailable")

    @babel.localeselector
    def get_locale():
        return util.get_locale()

    @babel.timezoneselector
    def get_timezone():
        user = getattr(g, 'user', None)
        if user is not None:
            return user.timezone
        return None

    @app.context_processor
    def inject_context():
        try:
            navtabs = util.get_navtabs()
        except Exception:
            navtabs = {}
        try:
            navtabs_index = util.get_navtabs_index()
        except Exception:
            navtabs_index = {}
        try:
            usercount = util.get_usercount()
        except Exception:
            usercount = 0
        try:
            videocount = util.get_videocount()
        except Exception:
            videocount = 0
        try:
            channelcount = util.get_channelcount()
        except Exception:
            channelcount = 0
        try:
            delchannelcount = util.get_delchannelcount()
        except Exception:
            delchannelcount = 0
        return dict(
            locale=util.get_locale(),
            theme=util.get_theme(),
            playnext=util.get_playnext(),
            autoplay=util.get_autoplay(),
            looplist=util.get_looplist(),
            current_url=quote_plus(request.url),
            current_path=quote_plus(request.full_path),
            navtabs=navtabs,
            navtabs_index=navtabs_index,
            usercount=usercount,
            videocount=videocount,
            channelcount=channelcount,
            delchannelcount=delchannelcount,
            url_orig='original_url'
        )

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
        return None

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

    _LINKIFY_ALLOWED_TAGS = {'a', 'br'}
    _LINKIFY_ALLOWED_ATTRS = {'a': {'href'}}

    @app.template_filter('linkify')
    def linkify(s):
        linked = bleach.linkify(str(s) if s is not None else '')
        return nh3.clean(linked, tags=_LINKIFY_ALLOWED_TAGS, attributes=_LINKIFY_ALLOWED_ATTRS)

    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

    @app.template_filter('nl2br')
    @pass_eval_context
    def nl2br(eval_ctx, value):
        result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                              for p in _paragraph_re.split(escape(value)))
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

    @app.template_filter('time_diff')
    def time_diff(s):
        now = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=60 * 3.4)
        return timeago.format(s, now)

    @app.template_filter('iso8601duration')
    def iso8601duration(seconds):
        try:
            seconds = int(seconds)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            duration = 'PT'
            if hours: duration += f'{hours}H'
            if minutes: duration += f'{minutes}M'
            if secs: duration += f'{secs}S'
            return duration or 'PT0S'
        except (ValueError, TypeError):
            return ''

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
            flash(request.url + ' ' + _l('not available'), 'error')
            return redirect(request.referrer or url_for('video.index'))
        app.logger.error(e)
        return render_template('video/404.html'), 404

    def internal_server_error(e):
        if has_request_context():
            app.logger.error('500 Internal Error: %s', request.url)
        else:
            app.logger.error(e)
        return render_template('video/500.html'), 500

    def service_unavailable(e):
        if has_request_context():
            app.logger.error('503 Service Unavailable: %s', request.url)
        else:
            app.logger.error(e)
        return render_template('video/503.html'), 503

    app.register_error_handler(400, bad_request)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(503, service_unavailable)


    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db_session.rollback()
        db_session.remove()

    from . import video, channel, about, category, language, settings, admin, playlist, theme, user, newsletter, donate, sitemap

    from alt2.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    app.register_blueprint(video.bp)
    app.register_blueprint(channel.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(category.bp)
    app.register_blueprint(language.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(playlist.bp)
    app.register_blueprint(theme.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(newsletter.bp)
    app.register_blueprint(donate.bp)
    app.register_blueprint(sitemap.bp)

    def url_for_other_page(page):
        args = request.view_args.copy()
        args['page'] = page
        return url_for(request.endpoint, **args)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page

    def url_for_cursor_page(cursor, page):
        args = request.view_args.copy()
        return url_for(request.endpoint, after=cursor, p=page, **args)

    app.jinja_env.globals['url_for_cursor_page'] = url_for_cursor_page

    return app
