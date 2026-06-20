import functools, hashlib, os, string, random, subprocess, requests, logging

logger = logging.getLogger(__name__)

from better_profanity import profanity
from captcha.image import ImageCaptcha
from datetime import datetime, timezone, timedelta, date
from email_validator import validate_email, EmailNotValidError
from flask import (
    session, request, redirect, url_for, current_app, flash, g
)
from sqlalchemy import func, nullslast, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm.attributes import flag_modified
from .database import db_session
from .models import Translation, Playlist, MvChannel, MvVideo, User, \
    EmailList, Entity, Source, Counter
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
        row = db_session.execute(
            select(Translation.varname, getattr(Translation, session['locale']))
        ).all()
        session['navtabs'] = dict(row)

    if 'navtabs_index' not in session:
        row = db_session.execute(select(Translation.varname, Translation.en)).all()
        session['navtabs_index'] = dict(row)

    if 'navtabs_perm' not in session:
        row = db_session.execute(
            select(Translation.varname, getattr(Translation, session['locale']))
        ).all()
        session['navtabs_perm'] = dict(row)

    if 'videocount' not in session:
        session['videocount'] = db_session.scalar(select(func.count(MvVideo.extractor_data)))
    if 'usercount' not in session:
        session['usercount'] = db_session.scalar(select(func.count(User.id)).filter(User.public))
    if 'playlistcount' not in session:
        session['playlistcount'] = db_session.scalar(
            select(func.count(Playlist.id)).filter(Playlist.public, Playlist.featured_video_id.isnot(None))
        )
    if 'channelcount' not in session:
        session['channelcount'] = db_session.scalar(select(func.count(MvChannel.ytc_id)))
    if 'delchannelcount' not in session:
        session['delchannelcount'] = db_session.scalar(
            select(func.count(MvChannel.ytc_id)).filter(MvChannel.ytc_deleted)
        )


def str_to_bool(s) -> object:
    if s == 'True':
        return True
    elif s == 'False':
        return False
    else:
        raise ValueError


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
    if session.get('email') is not None:
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
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return e


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
            if not result:
                flash(stderr.decode(errors='replace'), 'error')
            else:
                flash(result, 'success')
        except subprocess.TimeoutExpired:
            ssh.kill()
            ssh.communicate()
            flash('SSH command timed out', 'error')


def local_command(commands):
    for command in commands:
        localcmd = subprocess.Popen(['/bin/bash', '-c', command],
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        try:
            stdout, stderr = localcmd.communicate(timeout=30)
            result = stdout.splitlines()
            if not result:
                flash(stderr.decode(errors='replace'), 'error')
            else:
                flash(result, 'success')
        except subprocess.TimeoutExpired:
            localcmd.kill()
            localcmd.communicate()
            flash('Local command timed out', 'error')


def video_toggle_allow(video_id, bool_allow=None, bool_deleted=None):
    try:
        video = db_session.execute(
            select(Entity).filter(Entity.extractor_data == video_id)
        ).scalars().first()
        if bool_allow is not None:
            video.allow = bool_allow
        if bool_deleted is not None:
            video.yt_deleted = bool_deleted
        db_session.commit()
        return True
    except Exception:
        logger.exception("video_toggle_allow failed for video")
        return False


def channel_update(channel_id, delta=None, archive_type=None, deleted=None, viewcount=None, subscribercount=None, deleteddate=None):
    try:
        channel = db_session.execute(
            select(Source).filter(Source.ytc_id == channel_id)
        ).scalars().first()

        if delta:
            channel.delta = delta

        if archive_type:
            if archive_type == 'none':
                channel.ytc_archive = False
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = False
            elif archive_type == 'partial':
                channel.ytc_archive = False
                channel.ytc_partarchive = True
                channel.ytc_latestarchive = False
            elif archive_type == 'full':
                channel.ytc_archive = True
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = False
            elif archive_type == 'latest':
                channel.ytc_archive = False
                channel.ytc_partarchive = False
                channel.ytc_latestarchive = True

        if deleted is True or deleted is False:
            channel.ytc_deleted = deleted
        if viewcount:
            channel.ytc_viewcount = viewcount
        if subscribercount:
            channel.ytc_subscribercount = subscribercount
        if deleteddate:
            channel.ytc_deleteddate = deleteddate
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
        select(MvVideo).order_by(nullslast(MvVideo.ac_views.desc())),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def videos_latest(PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).order_by(nullslast(MvVideo.yt_deleted_date.desc())),
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
        select(MvVideo).order_by(MvVideo.yt_views.desc()),
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
        select(MvChannel).order_by(MvChannel.ytc_publishedat.desc(), MvChannel.ytc_id.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_popular(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.ytc_viewcount.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_deleted(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).filter(MvChannel.ytc_deleted)
        .order_by(MvChannel.ytc_deleteddate.desc(), MvChannel.ytc_id.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_limited(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).order_by(MvChannel.limited.desc(), MvChannel.ytc_id.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channels_archived(PER_PAGE, offset):
    return _exec_listing(
        select(MvChannel).filter(MvChannel.ytc_archive),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channeli(ytc_id):
    channel = db_session.get(MvChannel, ytc_id)
    if channel is None:
        channel = db_session.execute(
            select(MvChannel).filter(func.lower(MvChannel.ytc_id) == func.lower(ytc_id))
        ).scalar_one_or_none()
    return channel


@cache.memoize(timeout=3600)
def channeli_videocount(ytc_id):
    return db_session.scalar(
        select(func.count(MvVideo.extractor_data)).filter(MvVideo.ytc_id == ytc_id)
    )


@cache.memoize(timeout=3600)
def channeli_videos_newest(ytc_id, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.ytc_id == ytc_id).order_by(MvVideo.published.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def channeli_videos_popular(ytc_id, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.ytc_id == ytc_id).order_by(MvVideo.yt_views.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def ytc_popular(ytc_id, PER_PAGE, offset):
    return _exec_listing(
        select(MvVideo).filter(MvVideo.ytc_id == ytc_id).order_by(MvVideo.yt_views.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def playlists_newest(PER_PAGE, offset):
    return _exec_listing(
        select(Playlist).filter(Playlist.public, Playlist.featured_video_id.isnot(None))
        .order_by(Playlist.updated.desc()),
        PER_PAGE, offset,
    )


@cache.memoize(timeout=3600)
def playlists_popular(PER_PAGE, offset):
    return _exec_listing(
        select(Playlist).filter(Playlist.public, Playlist.featured_video_id.isnot(None))
        .order_by(Playlist.updated.desc()),
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
    return db_session.scalar(select(func.count(MvChannel.ytc_id)))


@cache.cached(key_prefix="cache:delchannelcount", timeout=3600)
def delchannelcount_cache():
    return db_session.scalar(select(func.count(MvChannel.ytc_id)).filter(MvChannel.ytc_deleted))


@cache.cached(key_prefix="cache:archivechannelcount", timeout=3600)
def archivechannelcount_cache():
    return db_session.scalar(select(func.count(MvChannel.ytc_id)).filter(MvChannel.ytc_archive))


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
        entity_video = db_session.execute(
            select(Entity).filter(Entity.extractor_data == video_id)
        ).scalar_one_or_none()
        today = str(date.today())
        myhash = int(hashlib.sha256(
            (ip + header + today + str(entity_video.extractor_data)).encode()
        ).hexdigest(), 16) % (2 ** 63)
        result = db_session.execute(
            pg_insert(Counter).values(hash=myhash).on_conflict_do_nothing(index_elements=['hash'])
        )
        if result.rowcount == 1:
            if entity_video.ac_views is None:
                entity_video.ac_views = 0
            entity_video.ac_views = entity_video.ac_views + 1
            flag_modified(entity_video, "ac_views")
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

    session['navtabs']['navtab1'] = user.navtabs[0]
    session['navtabs']['navtab2'] = user.navtabs[1]
    session['navtabs']['navtab3'] = user.navtabs[2]

    session['navtabs_index']['navtab1'] = BLUEPRINT_FIXES.get(user.navtabs_index[0], user.navtabs_index[0])
    session['navtabs_index']['navtab2'] = BLUEPRINT_FIXES.get(user.navtabs_index[1], user.navtabs_index[1])
    session['navtabs_index']['navtab3'] = BLUEPRINT_FIXES.get(user.navtabs_index[2], user.navtabs_index[2])


def logout_user_altcen():
    now = datetime.now(timezone.utc)
    user = db_session.execute(
        select(User).filter(User.id == session['user']['id'])
    ).scalar_one_or_none()
    user.updated = now
    user.settings = {
        "theme": session['theme'],
        "locale": session['locale'],
        "autoplay": session['autoplay'],
        "playnext": session['playnext']
    }

    user.navtabs = [session['navtabs']['navtab1'], session['navtabs']['navtab2'], session['navtabs']['navtab3']]
    user.navtabs_index = [session['navtabs_index']['navtab1'], session['navtabs_index']['navtab2'], session['navtabs_index']['navtab3']]
    db_session.commit()

    session['user'] = None


def verify_turnstile_token(token, secret_key):
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={'secret': secret_key, 'response': token},
        timeout=5,
    )
    return response.json()
