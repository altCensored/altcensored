import re, base64, functools, hashlib, hmac, os, secrets, string, random, subprocess, requests, logging, time

logger = logging.getLogger(__name__)

from better_profanity import profanity
from captcha.image import ImageCaptcha
from datetime import datetime, timezone, timedelta, date
from email_validator import validate_email, EmailNotValidError
from urllib.parse import urlsplit
from flask import (
    session, request, redirect, url_for, current_app, flash, g
)
from sqlalchemy import any_, func, literal, not_, nullslast, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm.attributes import flag_modified
from .database import db_session
from .models import Translation, Playlist, MvChannel, MvVideo, User, \
    EmailList, Video, Source, Counter
from . import config
from .cache import cache

# Re-exports for backward compatibility — callers continue to import from util
from .services.email import (
    generate_confirmation_token, confirm_token,
    send_confirm_email, send_forgot_password_email,
    send_sgrid_email, send_all_mass_email,
)
from .services.archive import (
    get_video_files, get_video_files_2, get_image_file, check_video_files,
    ac_object_exist, check_ac_object_exists, site_is_online, get_ia_item,
)

url_orig = 'original_url'


def get_current_user():
    """Return the logged-in User ORM object for this request, or None.

    Result is cached on flask.g so the DB is hit at most once per request,
    and only on requests that actually need user data.
    """
    if not hasattr(g, '_current_user_loaded'):
        if session.get('user') is not None:
            g._current_user = db_session.execute(
                select(User).filter(User.id == session['user']['id'])
            ).scalar_one_or_none()
        else:
            g._current_user = None
        g._current_user_loaded = True
    return g._current_user


BLUEPRINT_FIXES = {
    'kanal': 'channel', 'canale': 'channel', 'kanaal': 'channel',
    'videos': 'video',
}


def get_locale():
    if 'locale' in session:
        return session['locale']
    else:
        session['locale'] = request.accept_languages.best_match(config.SUPPORTED_LANGUAGES.keys(), default='en')
    return session['locale']


def get_theme():
    if 'theme' in session:
        return session['theme']
    else:
        session['theme'] = config.DEFAULT_THEME
    return session['theme']


def get_playnext():
    if 'playnext' in session:
        return session['playnext']
    else:
        session['playnext'] = config.DEFAULT_PLAYNEXT
    return session['playnext']


def get_looplist():
    if 'looplist' in session:
        return session['looplist']
    else:
        session['looplist'] = config.DEFAULT_LOOPLIST
    return session['looplist']


def get_autoplay():
    if 'autoplay' in session:
        return session['autoplay']
    else:
        session['autoplay'] = config.DEFAULT_AUTOPLAY
    return session['autoplay']


def get_navtabs():
    if 'navtabs' in session:
        return session['navtabs']
    locale = get_locale()  # ensures session['locale'] is set before we query
    row = navtabs_cache(locale)
    session['navtabs'] = dict(row)
    return session['navtabs']


def get_navtabs_index():
    if 'navtabs_index' in session:
        return session['navtabs_index']
    row = navtabs_index_cache()
    session['navtabs_index'] = dict(row)
    return session['navtabs_index']


def get_videocount():
    if 'videocount' in session:
        return session['videocount']
    else:
        session['videocount'] = videocount_cache()
    return session['videocount']


def get_channelcount():
    if 'channelcount' in session:
        return session['channelcount']
    else:
        session['channelcount'] = channelcount_cache()
    return session['channelcount']


def get_delchannelcount():
    if 'delchannelcount' in session:
        return session['delchannelcount']
    else:
        session['delchannelcount'] = delchannelcount_cache()
    return session['delchannelcount']


def get_archivechannelcount():
    if 'archivechannelcount' in session:
        return session['archivechannelcount']
    else:
        session['archivechannelcount'] = archivechannelcount_cache()
    return session['archivechannelcount']


def get_playlistcount():
    if 'playlistcount' in session:
        return session['playlistcount']
    else:
        session['playlistcount'] = playlistcount_cache()
    return session['playlistcount']


def get_usercount():
    if 'usercount' in session:
        return session['usercount']
    else:
        session['usercount'] = usercount_cache()
    return session['usercount']


# Static session keys with their defaults
_SESSION_STATIC_DEFAULTS = {
    'theme': 'light',
    'playnext': False,
    'looplist': True,
}


def set_session():
    for key, value in _SESSION_STATIC_DEFAULTS.items():
        session.setdefault(key, value)

    if 'locale' not in session:
        session['locale'] = request.accept_languages.best_match(
            config.SUPPORTED_LANGUAGES.keys(), default='en'
        )

    if 'navtabs' not in session:
        session['navtabs'] = dict(navtabs_cache(session['locale']))

    if 'navtabs_index' not in session:
        session['navtabs_index'] = dict(navtabs_index_cache())

    if 'navtabs_perm' not in session:
        session['navtabs_perm'] = dict(navtabs_cache(session['locale']))

    if 'videocount' not in session:
        session['videocount'] = videocount_cache()
    if 'usercount' not in session:
        session['usercount'] = usercount_cache()
    if 'playlistcount' not in session:
        session['playlistcount'] = playlistcount_cache()
    if 'channelcount' not in session:
        session['channelcount'] = channelcount_cache()
    if 'delchannelcount' not in session:
        session['delchannelcount'] = delchannelcount_cache()


def str_to_bool(s) -> object:
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError

string_boolean = str_to_bool


def contains_profanity(dirty_text):
    return profanity.contains_profanity(dirty_text)


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None:
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view


def admin_login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user') is None or session['user']['username'] != 'admin':
            return redirect(url_for('video.index'))
        return view(**kwargs)
    return wrapped_view



def email_exists(email):
    if session.get('user') is not None:
        if email == session['user']['email']:
            return False
    if db_session.scalar(select(User.email).filter(func.lower(User.email) == func.lower(email))) is not None:
        return True


def email_list_exists(email):
    if db_session.scalar(
        select(EmailList.email).filter(func.lower(EmailList.email) == func.lower(email))
    ) is not None:
        return True


def validate_user_email(email):
    """Returns None if valid, or an EmailNotValidError if invalid."""
    try:
        validate_email(email)
    except EmailNotValidError as e:
        return e
    return None


def username_exists(username):
    if username == session['user']['username']:
        return False
    if db_session.scalar(
        select(User.username).filter(func.lower(User.username) == func.lower(username))
    ) is not None:
        return True


def generate_random(size=4, chars=string.ascii_uppercase):
    return ''.join(random.choice(chars) for _ in range(size))


def create_captcha(myrandom, mycaptcha):
    image = ImageCaptcha()
    data = image.generate(str(myrandom))
    image.write(str(myrandom), os.path.join(current_app.static_folder, mycaptcha))


def title_exists(ftitle):
    user_id = session['user']['id']
    if db_session.scalar(
        select(Playlist.title).filter(Playlist.title == ftitle, Playlist.user_id == user_id)
    ) is not None:
        return True



VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,24}$')
MAX_LIST_VIDEOS = 2000
_EMPTY_ARRAY = text("'{}'::text[]")


def valid_video_id(v):
    """extractor_data values are 1-24 chars of [A-Za-z0-9_-] (11 for videos, 24 for channels)."""
    return isinstance(v, str) and VIDEO_ID_RE.match(v) is not None


def _append_to_array(model, where_id, column, v, extra_values=None):
    """Append v to an ARRAY(text) column in one UPDATE, so concurrent adds cannot overwrite each other.

    Returns 'added', 'exists' (already in the list) or 'full' (MAX_LIST_VIDEOS reached).
    The caller commits.
    """
    col = getattr(model, column)
    arr = func.coalesce(col, _EMPTY_ARRAY)
    values = {column: func.array_append(arr, v), 'updated': func.now()}
    values.update(extra_values(arr) if extra_values else {})
    res = db_session.execute(
        update(model)
        .where(model.id == where_id,
               not_(literal(v) == any_(arr)),
               func.cardinality(arr) < MAX_LIST_VIDEOS)
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if res.rowcount:
        return 'added'
    current = db_session.execute(select(col).where(model.id == where_id)).scalar() or []
    return 'exists' if v in current else 'full'


def add_to_watchlater(user_id, v):
    return _append_to_array(User, user_id, 'watchlater', v)


def add_to_playlist(playlist_id, v):
    return _append_to_array(
        Playlist, playlist_id, 'videos', v,
        extra_values=lambda arr: {
            'video_count': func.cardinality(arr) + 1,
            'featured_video_id': func.coalesce(func.nullif(Playlist.featured_video_id, ''), v),
        })


def safe_next(default='/'):
    """Return the ?original_url= target as a same-site relative path, else default.

    Templates pass current_url as an absolute URL, so accept our own host and
    reduce it to path?query; anything pointing elsewhere falls back to default.
    """
    raw = request.values.get(url_orig)
    if not raw:
        return default
    try:
        parts = urlsplit(raw)
    except ValueError:
        return default
    if parts.scheme not in ('', 'http', 'https'):
        return default
    if parts.netloc:
        hosts = {request.host.lower(), config.MYSERVER_NAME.lower()}
        if parts.netloc.lower() not in hosts:
            return default
    path = parts.path or '/'
    if not path.startswith('/') or path.startswith('//') or '\\' in path:
        return default
    return path + ('?' + parts.query if parts.query else '')


def ssh_command(sys_name, commands, sys_user='root'):
    ssh_host = sys_user + '@' + sys_name
    for command in commands:
        ssh = subprocess.Popen(["ssh", "-o", "StrictHostKeyChecking=accept-new", "%s" % ssh_host, command],
                               shell=False,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        try:
            stdout, stderr = ssh.communicate(timeout=30)
            result = stdout.splitlines()
            if result:
                flash(b'\n'.join(result).decode(errors='replace'), 'success')
            else:
                error_msg = stderr.decode(errors='replace').strip()
                if error_msg:
                    flash(error_msg, 'error')
        except subprocess.TimeoutExpired:
            ssh.kill()
            ssh.communicate()
            flash('SSH command timed out', 'error')


def local_command(commands, timeout=30):
    for command in commands:
        localcmd = subprocess.Popen(['/bin/bash', '-c', command],
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        try:
            stdout, stderr = localcmd.communicate(timeout=timeout)
            result = stdout.splitlines()
            if result:
                flash(b'\n'.join(result).decode(errors='replace'), 'success')
            else:
                error_msg = stderr.decode(errors='replace').strip()
                if error_msg:
                    flash(error_msg, 'error')
        except subprocess.TimeoutExpired:
            localcmd.kill()
            localcmd.communicate()
            flash('Local command timed out', 'error')


def video_toggle_allow(video_id, bool_allow=None, bool_deleted=None):
    try:
        video = db_session.execute(
            select(Video).filter(Video.extractor_data == video_id)
        ).scalars().first()
        if bool_allow is not None:
            video.allow = bool_allow
        if bool_deleted is not None:
            video.deleted = bool_deleted
        db_session.commit()
        return True
    except Exception:
        logger.exception("video_toggle_allow failed for video")
        return False


def channel_update(channel_id, delta=None, archive_type=None, deleted=None, viewcount=None, subscribercount=None, deleteddate=None):
    try:
        channel = db_session.execute(
            select(Source).filter(Source.extractor_data == channel_id)
        ).scalars().first()

        if channel is None:
            logger.warning("channel_update: channel_id=%s not found", channel_id)
            return False

        if delta:
            channel.delta = delta

        if archive_type:
            if archive_type == 'none':
                channel.archive_full = False
                channel.archive_part = False
                channel.archive_latest = False
            elif archive_type == 'partial':
                channel.archive_full = False
                channel.archive_part = True
                channel.archive_latest = False
            elif archive_type == 'full':
                channel.archive_full = True
                channel.archive_part = False
                channel.archive_latest = False
            elif archive_type == 'latest':
                channel.archive_full = False
                channel.archive_part = False
                channel.archive_latest = True

        if deleted is True or deleted is False:
            channel.deleted = deleted
        if deleted is False:
            # same as yt-syncac toggle_source(): an undeleted channel has no deleted date
            channel.deleted_date = None
        if viewcount:
            channel.view_count = viewcount
        if subscribercount:
            channel.channel_follower_count = subscribercount
        if deleteddate and deleted is not False:
            channel.deleted_date = deleteddate
        db_session.commit()
        return True
    except Exception:
        logger.exception("channel_update failed for channel_id=%s", channel_id)
        return False


# Private helper for cached paginated listings
def _exec_listing(stmt, per_page, offset):
    return db_session.execute(stmt.limit(per_page).offset(offset)).scalars().all()


@cache.memoize(timeout=3600)
def videos_trending(PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).order_by(nullslast(MvVideo.view_count_ac.desc())),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def videos_latest(PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).order_by(nullslast(MvVideo.deleted_date.desc())),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def videos_newest(PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).order_by(MvVideo.published.desc(), MvVideo.extractor_data.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def videos_popular(PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).order_by(MvVideo.view_count.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_latest(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.id.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_newest(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.published_at.desc(), MvChannel.extractor_data.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_popular(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.view_count.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_deleted(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).filter(MvChannel.deleted)
        .order_by(MvChannel.deleted_date.desc(), MvChannel.extractor_data.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_limited(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.limited.desc(), MvChannel.extractor_data.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_archived(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).filter(MvChannel.archive_full),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channeli(ytc_id):
    channel = db_session.execute(
        select(MvChannel).filter(MvChannel.extractor_data == ytc_id)
    ).scalar_one_or_none()
    if channel is None:
        channel = db_session.execute(
            select(MvChannel).filter(func.lower(MvChannel.extractor_data) == func.lower(ytc_id))
        ).scalar_one_or_none()
    return channel


@cache.memoize(timeout=3600)
def channeli_videocount(ytc_id):
    return db_session.scalar(
        select(func.count(MvVideo.extractor_data)).filter(MvVideo.source_extractor_data == ytc_id)
    )


@cache.memoize(timeout=3600)
def channeli_videos_newest(ytc_id, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.source_extractor_data == ytc_id).order_by(MvVideo.published.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channeli_videos_popular(ytc_id, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.source_extractor_data == ytc_id).order_by(MvVideo.view_count.desc()),
        PER_PAGE, offset,
    )




@cache.memoize(timeout=3600)
def playlisti(playlist):
    return db_session.execute(
        select(Playlist).filter(Playlist.hashid == playlist)
    ).scalar_one_or_none()


@cache.memoize(timeout=3600)
def playlisti_videocount(playlist):
    return db_session.scalar(
        select(func.count(MvVideo.id)).filter(MvVideo.extractor_data.in_(playlist.videos))
    )


@cache.memoize(timeout=3600)
def playlisti_videos(playlist, ordering, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.extractor_data.in_(playlist.videos)).order_by(ordering),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def users_newest(PER_PAGE, offset):
    return _exec_listing(
        select(User).filter(User.public).order_by(User.id.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def users_popular(PER_PAGE, offset):
    return _exec_listing(
        select(User).filter(User.public).order_by(User.view_counter.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def useri(username):
    return db_session.execute(
        select(User).filter(func.lower(User.username) == func.lower(username))
    ).scalar_one_or_none()


@cache.cached(key_prefix="cache:videocount", timeout=3600)
def videocount_cache():
    return db_session.scalar(select(func.count(MvVideo.extractor_data)))


@cache.cached(key_prefix="cache:channelcount", timeout=3600)
def channelcount_cache():
    return db_session.scalar(select(func.count(MvChannel.extractor_data)))


@cache.cached(key_prefix="cache:delchannelcount", timeout=3600)
def delchannelcount_cache():
    return db_session.scalar(select(func.count(MvChannel.extractor_data)).filter(MvChannel.deleted))


@cache.cached(key_prefix="cache:archivechannelcount", timeout=3600)
def archivechannelcount_cache():
    return db_session.scalar(select(func.count(MvChannel.extractor_data)).filter(MvChannel.archive_full))


@cache.cached(key_prefix="cache:playlistcount", timeout=3600)
def playlistcount_cache():
    return db_session.scalar(
        select(func.count(Playlist.id)).filter(Playlist.public, Playlist.featured_video_id.isnot(None))
    )


@cache.cached(key_prefix="cache:usercount", timeout=3600)
def usercount_cache():
    return db_session.scalar(select(func.count(User.id)).filter(User.public))


@cache.memoize(timeout=3600)
def navtabs_cache(locale):
    return db_session.execute(
        select(Translation.varname, getattr(Translation, locale))
    ).all()


@cache.cached(key_prefix="cache:navtabs_index", timeout=3600)
def navtabs_index_cache():
    return db_session.execute(select(Translation.varname, Translation.en)).all()



def increment_video_counter(video_id, ip, header):
    try:
        video_row = db_session.execute(
            select(Video).filter(Video.extractor_data == video_id)
        ).scalar_one_or_none()
        today = str(date.today())
        myhash = int(hashlib.sha256(
            (ip + header + today + str(video_row.extractor_data)).encode()
        ).hexdigest(), 16) % (2 ** 63)
        result = db_session.execute(
            pg_insert(Counter).values(hash=myhash).on_conflict_do_nothing(index_elements=['hash'])
        )
        if result.rowcount == 1:
            if video_row.view_count_ac is None:
                video_row.view_count_ac = 0
            video_row.view_count_ac = video_row.view_count_ac + 1
            flag_modified(video_row, "view_count_ac")
            db_session.commit()
    except Exception:
        logger.exception("increment_video_counter failed for video_id=%s", video_id)
        db_session.rollback()
    finally:
        db_session.remove()


def create_user_altcen(user):
    now = datetime.now(timezone.utc)
    navtabs_value = [session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3']]
    navtabs_index_value = [session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'],
                           session['navtabs_index']['navtab3']]
    user.description = ""
    user.created_date = now
    user.updated = now
    user.email_lastsent_date = datetime.now(timezone.utc) - timedelta(30)
    user.email_verified = False
    user.view_counter = 0
    user.watched = []
    user.watchlater = []
    user.settings = {
        "theme": session['theme'],
        "locale": session['locale'],
        "autoplay": session['autoplay'],
        "playnext": session['playnext'],
        "looplist": session['looplist']
    }
    user.navtabs = navtabs_value
    user.navtabs_index = navtabs_index_value
    db_session.add(user)
    db_session.commit()
    return user


def login_user_altcen(user):
    session['user'] = dict(id=user.id,
                           email=user.email,
                           username=user.username,
                           description=user.description,
                           public=user.public,
                           email_subscribed=user.email_subscribed,
                           email_verified=user.email_verified,
                           contributor=user.contributor
                           )
    newSettings = dict(user.settings)
    autoplayg = user.settings.get("autoplay")

    session['locale'] = newSettings['locale']
    session['theme'] = newSettings['theme']
    session['autoplay'] = autoplayg
    session['playnext'] = newSettings['playnext']
    session['looplist'] = newSettings.get('looplist', config.DEFAULT_LOOPLIST)

    session['navtabs']['navtab1'] = user.navtabs[0]
    session['navtabs']['navtab2'] = user.navtabs[1]
    session['navtabs']['navtab3'] = user.navtabs[2]

    session['navtabs_index']['navtab1'] = BLUEPRINT_FIXES.get(user.navtabs_index[0], user.navtabs_index[0])
    session['navtabs_index']['navtab2'] = BLUEPRINT_FIXES.get(user.navtabs_index[1], user.navtabs_index[1])
    session['navtabs_index']['navtab3'] = BLUEPRINT_FIXES.get(user.navtabs_index[2], user.navtabs_index[2])


def logout_user_altcen():
    # /auth/logout can be hit without a login (bots, expired session)
    if not session.get('user'):
        session['user'] = None
        return
    now = datetime.now(timezone.utc)
    user = db_session.execute(
        select(User).filter(User.id == session['user']['id'])
    ).scalar_one_or_none()
    if user is None:
        session['user'] = None
        return
    user.updated = now
    user.settings = {
        "theme": session['theme'],
        "locale": session['locale'],
        "autoplay": session['autoplay'],
        "playnext": session['playnext'],
        "looplist": session['looplist'],
    }

    user.navtabs = [session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3']]
    user.navtabs_index = [session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3']]
    db_session.commit()

    session['user'] = None


LOGGEDIN_MAX_AGE = 86400


def _loggedin_sig(expires):
    # nginx secure_link format: base64url(md5("<expires> <secret>")), no padding
    digest = hashlib.md5(f"{expires} {config.LOGGEDIN_SECRET}".encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


def make_loggedin_cookie():
    """Value for the 'loggedin' cookie that nginx uses to exempt logged-in users from anon limits."""
    if not config.LOGGEDIN_SECRET:
        logger.warning("ALTC_LOGGEDIN_SECRET unset, issuing unsigned loggedin cookie")
        return secrets.token_hex(32)
    expires = int(time.time()) + LOGGEDIN_MAX_AGE
    return f"{expires}.{_loggedin_sig(expires)}"


def loggedin_cookie_valid(value, min_remaining=0):
    if not config.LOGGEDIN_SECRET or not value:
        return False
    expires, _, sig = value.partition('.')
    if not (len(expires) == 10 and expires.isdigit()):
        return False
    if not hmac.compare_digest(sig, _loggedin_sig(expires)):
        return False
    return int(expires) > time.time() + min_remaining


def set_loggedin_cookie(response):
    response.set_cookie('loggedin', make_loggedin_cookie(), httponly=True, samesite='Lax', secure=True,
                        max_age=LOGGEDIN_MAX_AGE)


def verify_turnstile_token(token, secret_key):
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={'secret': secret_key, 'response': token},
        timeout=5,
    )
    return response.json()
