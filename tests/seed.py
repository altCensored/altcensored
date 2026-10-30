"""Small, known dataset. Assertions in the tests rely on these exact values.

  channels  UCaaaaaaaaaaaaaaaaaaaaaa  "Alpha Channel"  archived, 3 videos
            UCbbbbbbbbbbbbbbbbbbbbbb  "Beta Channel"   archived + deleted on YT, 1 video
  videos    vid_live_0001  on YouTube, not archived
            vid_ia_00002   deleted on YT, archived on Internet Archive
            vid_ac_00003   deleted on YT, archived on our own storage (exists_ac)
            vid_gone_0004  deleted on YT, nowhere (Beta Channel)

The ``mv_*`` materialized views are the real ones, exported from prod to
fixtures/matviews.sql. ``load`` seeds the base tables and refreshes them, as
the scraper does, so a video reaches ``mv_video`` only if prod's view
definition lets it (vid_gone_0004 must stay out).
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from altcen_models.db import Source, Video

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 1, 12, 0, 0)

CHANNELS = [
    dict(ytc_id="UCaaaaaaaaaaaaaaaaaaaaaa", ytc_title="Alpha Channel",
         ytc_deleted=False, ytc_archive=True),
    dict(ytc_id="UCbbbbbbbbbbbbbbbbbbbbbb", ytc_title="Beta Channel",
         ytc_deleted=True, ytc_archive=True),
]

VIDEOS = [
    # id, title, channel index, yt_deleted, exists_ia, exists_ac
    ("vid_live_0001", "Live video", 0, False, None, None),
    ("vid_ia_00002", "Deleted, on IA", 0, True, True, None),
    ("vid_ac_00003", "Deleted, on our storage", 0, True, False, True),
    ("vid_gone_0004", "Deleted, nowhere", 1, True, False, False),
]


def load(engine):
    _load_csv_tables(engine)
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
    refresh_matviews(engine)


MATVIEWS = ("mv_video", "mv_altcen_user", "mv_category", "mv_channel",
            "mv_playlist")  # dependency order: mv_category reads mv_video


def create_matviews(engine):
    sql = (FIXTURES / "matviews.sql").read_text()
    with engine.begin() as conn:
        conn.exec_driver_sql(sql.replace("%", "%%"))


def refresh_matviews(engine):
    with engine.begin() as conn:
        for mv in MATVIEWS:
            conn.exec_driver_sql(f"REFRESH MATERIALIZED VIEW {mv}")


def _load_csv_tables(engine):
    """UI text exported from prod (translation, language): templates need the
    real navbar keys, and inventing them would drift from the site.
    Plain inserts, not COPY: psycogreen makes the connection asynchronous,
    and psycopg2 refuses copy_expert on those."""
    with engine.begin() as conn:
        for table in ("translation", "language"):
            with open(FIXTURES / f"{table}.csv", newline="") as f:
                rows = [{k: (v if v != "" else None) for k, v in r.items()}
                        for r in csv.DictReader(f)]
            cols = list(rows[0])
            conn.execute(
                text(f"INSERT INTO {table} ({', '.join(cols)}) "
                     f"VALUES ({', '.join(':' + c for c in cols)})"),
                rows)
