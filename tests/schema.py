"""Column and field names that differ between the legacy and ytac schemas, so
tests can assert on database state without branching inline."""
from tests.seed import BACKEND

if BACKEND == "legacy":
    # source is joined to entity: ytc_id lives on source, extractor_data on entity
    CHANNEL_WHERE = "ytc_id = :c"
    CHANNEL_FLAGS = "ytc_archive, ytc_partarchive, ytc_latestarchive, ytc_deleted"
    CHANNEL_POST_ARCHIVE = "ytc_archive"     # JSON field of POST channel_table_new_data
    CHANNEL_POST_TITLE = "ytc_title"
    CHANNEL_TITLE_COL = "ytc_title"
    VIDEO_TABLE = "entity"
    VIDEO_DELETED = "yt_deleted"
else:
    CHANNEL_WHERE = "extractor_data = :c"
    CHANNEL_FLAGS = "archive_full, archive_part, archive_latest, deleted"
    CHANNEL_POST_ARCHIVE = "archive_full"
    CHANNEL_POST_TITLE = "title"
    CHANNEL_TITLE_COL = "title"
    VIDEO_TABLE = "video"
    VIDEO_DELETED = "deleted"

if BACKEND == "legacy":
    # yt-syncac gets the channel's uploads-playlist URL (UC.. becomes UU..)
    ADD_VERB = "afs"
    VIDEO_DATA_ALL = 6   # queries Entity, so the 2 channels are listed too

    def channel_ref(channel_id):
        return "UU" + channel_id[2:]
else:
    # ytac gets the channel id itself
    ADD_VERB = "add"
    VIDEO_DATA_ALL = 4

    def channel_ref(channel_id):
        return channel_id

ALPHA = "UCaaaaaaaaaaaaaaaaaaaaaa"
BETA = "UCbbbbbbbbbbbbbbbbbbbbbb"
