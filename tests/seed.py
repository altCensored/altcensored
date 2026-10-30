"""Small, known dataset. Assertions in the tests rely on these exact values.

  channels  UCaaaaaaaaaaaaaaaaaaaaaa  "Alpha Channel"  archived, 3 videos
            UCbbbbbbbbbbbbbbbbbbbbbb  "Beta Channel"   archived + deleted on YT, 1 video
  videos    vid_live_0001  on YouTube, not archived
            vid_ia_00002   deleted on YT, archived on Internet Archive
            vid_ac_00003   deleted on YT, archived on our own storage
            vid_gone_0004  deleted on YT, nowhere (Beta Channel)

The data is one neutral spec; two loaders write it into either schema:
``legacy`` (altcen_models: Entity/Source/Video) or ``ytac`` (the cutover
package). The backend is whichever package the venv has. The materialized
views are real ones: legacy loads prod's DDL from fixtures/matviews.sql, ytac
uses its own ytac.views. Rows are seeded into base tables and the views
refreshed, as the scraper does, so a video reaches ``mv_video`` only if the
view definition lets it (vid_gone_0004 must stay out).
"""
import csv
from datetime import datetime, timedelta
from importlib.util import find_spec
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

BACKEND = "legacy" if find_spec("altcen_models") else "ytac"
FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 1, 12, 0, 0)

CHANNELS = [
    dict(ytc_id="UCaaaaaaaaaaaaaaaaaaaaaa", ytc_title="Alpha Channel",
         ytc_deleted=False, ytc_archive=True),
    dict(ytc_id="UCbbbbbbbbbbbbbbbbbbbbbb", ytc_title="Beta Channel",
         ytc_deleted=True, ytc_archive=True),
]

VIDEOS = [
    # id, title, channel index, yt_deleted, on IA, on own storage
    ("vid_live_0001", "Live video", 0, False, None, None),
    ("vid_ia_00002", "Deleted, on IA", 0, True, True, None),
    ("vid_ac_00003", "Deleted, on our storage", 0, True, False, True),
    ("vid_gone_0004", "Deleted, nowhere", 1, True, False, False),
]

# legacy view creation order matters: mv_category reads mv_video
MATVIEWS = ("mv_video", "mv_altcen_user", "mv_category", "mv_channel",
            "mv_playlist")


def setup(engine):
    """Empty the test DB, build the schema and views, load and refresh."""
    wipe(engine)
    if BACKEND == "legacy":
        from alt2.models import Base
        # the mv_* ORM models are only mappings; real views come from prod's DDL
        real = [t for n, t in Base.metadata.tables.items()
                if not n.startswith("mv_")]
        Base.metadata.create_all(engine, tables=real)
        with engine.begin() as conn:
            conn.exec_driver_sql((FIXTURES / "matviews.sql").read_text())
        _load_legacy(engine)
    else:
        from alt2.models import Base
        from ytac import views
        Base.metadata.create_all(engine)
        with Session(engine) as s:
            views.create_all(s)
        _load_ytac(engine)
    _load_accounts(engine)
    _load_ui_text(engine)
    refresh_matviews(engine)


def wipe(engine):
    """Drop every view and table, whichever schema left them behind. The DB is
    dedicated to tests (conftest enforces the _test name)."""
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            DO $$ DECLARE r record; BEGIN
              FOR r IN SELECT matviewname AS n FROM pg_matviews
                        WHERE schemaname = 'public' LOOP
                EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS ' || quote_ident(r.n) || ' CASCADE';
              END LOOP;
              FOR r IN SELECT tablename AS n FROM pg_tables
                        WHERE schemaname = 'public' LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.n) || ' CASCADE';
              END LOOP;
            END $$""")


def refresh_matviews(engine):
    with engine.begin() as conn:
        names = conn.exec_driver_sql(
            "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'"
        ).scalars().all()
        for mv in [m for m in MATVIEWS if m in names]:
            conn.exec_driver_sql(f"REFRESH MATERIALIZED VIEW {mv}")


def _load_legacy(engine):
    from altcen_models.db import Source, Video
    with Session(engine) as s:
        sources = []
        for i, c in enumerate(CHANNELS):
            src = Source(
                extractor_key="Youtube", extractor_data=c["ytc_id"],
                title=c["ytc_title"], delta=timedelta(days=7),
                url=f"https://www.youtube.com/channel/{c['ytc_id']}",
                extractor_match="YoutubeTab", ytc_archive=c["ytc_archive"],
                ytc_deleted=c["ytc_deleted"],
                ytc_deleteddate=NOW if c["ytc_deleted"] else None,
                ytc_title=c["ytc_title"], ytc_id=c["ytc_id"],
                ytc_publishedat=NOW - timedelta(days=900),
                ytc_viewcount=1000 * (i + 1), ytc_subscribercount=10 * (i + 1),
            )
            s.add(src)
            sources.append(src)
        for n, (vid, title, ch, deleted, ia, ac) in enumerate(VIDEOS):
            v = Video(
                extractor_key="Youtube", extractor_data=vid, title=title,
                prev=NOW, published=NOW - timedelta(days=30 - n),
                yt_deleted=deleted,
                yt_deleted_date=NOW if deleted else None,
                exists_ia=ia, exists_ac=ac, duration=120 + n,
                yt_views=100 * (n + 1),
            )
            v.sources.append(sources[ch])
            s.add(v)
        s.commit()


def _load_ytac(engine):
    """Same data in the ytac schema. Its flags are NOT NULL booleans, so the
    legacy tri-state exists_ia (None = unknown) collapses to False."""
    from ytac.db import Source, Video
    with Session(engine) as s:
        sources = []
        for i, c in enumerate(CHANNELS):
            src = Source(
                extractor_data=c["ytc_id"], title=c["ytc_title"],
                url=f"https://www.youtube.com/channel/{c['ytc_id']}",
                delta=timedelta(days=7), deleted=c["ytc_deleted"],
                deleted_date=NOW.date() if c["ytc_deleted"] else None,
                archive_full=c["ytc_archive"],
                published_at=(NOW - timedelta(days=900)).date(),
                view_count=1000 * (i + 1), channel_follower_count=10 * (i + 1),
            )
            s.add(src)
            sources.append(src)
        for n, (vid, title, ch, deleted, ia, ac) in enumerate(VIDEOS):
            v = Video(
                extractor_data=vid, title=title,
                published=(NOW - timedelta(days=30 - n)).date(),
                deleted=deleted, deleted_date=NOW.date() if deleted else None,
                ia_exists=bool(ia), ac_exists=bool(ac), duration=120 + n,
                view_count=100 * (n + 1),
            )
            v.sources.append(sources[ch])
            s.add(v)
        s.commit()


PASSWORD = "test-password"
# username, email, verified. "admin" is special: admin_login_required checks it.
USERS = [
    ("admin", "admin@example.test", True),
    ("alice", "alice@example.test", True),
    ("newbie", "newbie@example.test", False),
]
CATEGORIES = ["Music", "News"]
PLAYLIST = dict(hashid="plAliceOne01", title="Alice list",
                videos=["vid_ia_00002", "vid_ac_00003"])


def _load_accounts(engine):
    """Users (all share PASSWORD), two categories and one public playlist owned
    by alice. User and Playlist have the same columns on both schemas;
    Category was renamed by ytac, hence the branch."""
    from alt2.models import Category, Playlist, User
    with Session(engine) as s:
        users = {}
        for name, email, verified in USERS:
            u = User(username=name, email=email, email_verified=verified,
                     description="", view_counter=0, watched=[], watchlater=[],
                     created_date=NOW, updated=NOW,
                     email_lastsent_date=NOW - timedelta(days=30),
                     settings=dict(theme="light", locale="en", autoplay="True",
                                   playnext="True", looplist="True"),
                     navtabs=["video", "channel", "playlist"],
                     navtabs_index=["video", "channel", "playlist"])
            u.set_password(PASSWORD)
            s.add(u)
            users[name] = u
        s.flush()
        for n, name in enumerate(CATEGORIES, start=1):
            if BACKEND == "legacy":
                s.add(Category(cat_id=n, cat_name=name, cat_image=f"{name}.png"))
            else:
                s.add(Category(id=n, name=name, icon=f"{name}.png"))
        s.add(Playlist(user_id=users["alice"].id, public=True, view_counter=0,
                       video_count=len(PLAYLIST["videos"]), created=NOW,
                       updated=NOW, **PLAYLIST))
        s.commit()


# fixtures/*.csv use the legacy column names; ytac renamed some
_YTAC_LANGUAGE = {"lang_id": "id", "lang_name": "name", "lang_code": "code",
                  "lang_image": "flag", "lang_image_css": "flag_icon",
                  "lang_tagstring": "tag_filter"}


def _load_ui_text(engine):
    """UI text exported from prod (translation, language): templates need the
    real navbar keys, and inventing them would drift from the site.
    Plain inserts, not COPY: psycogreen makes the connection asynchronous,
    and psycopg2 refuses copy_expert on those."""
    with engine.begin() as conn:
        for table in ("translation", "language"):
            with open(FIXTURES / f"{table}.csv", newline="") as f:
                rows = [{k: (v if v != "" else None) for k, v in r.items()}
                        for r in csv.DictReader(f)]
            if BACKEND == "ytac" and table == "language":
                rows = [{_YTAC_LANGUAGE[k]: v for k, v in r.items()}
                        for r in rows]
            cols = list(rows[0])
            conn.execute(
                text(f"INSERT INTO {table} ({', '.join(cols)}) "
                     f"VALUES ({', '.join(':' + c for c in cols)})"),
                rows)
