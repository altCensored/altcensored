"""Player-side endpoints: embed, video-sources, ping-view, play-next, the
watch page for a logged-in user, and the search variants."""
import json

import pytest

from tests import schema
from tests.conftest import login
from tests.seed import PLAYLIST

HASH = PLAYLIST["hashid"]
IA_URL = "https://ia.test/x"
UA = {"User-Agent": "pytest-agent"}


@pytest.fixture(autouse=True)
def archive_stubs(monkeypatch):
    """Replace the autouse network guards with canned answers."""
    import alt2.video
    monkeypatch.setattr(alt2.video, "get_ia_item", lambda vid: IA_URL)
    monkeypatch.setattr(alt2.video, "check_ac_object_exists", lambda vid: True)


class JoinedThread:
    """Start a real thread and wait for it, so the view counter is written
    before the response returns instead of racing the assertion. It must stay a
    separate thread: increment_video_counter ends in db_session.remove(), which
    would detach the request's own objects if it ran inline."""
    def __init__(self, target, args=()):
        import threading
        self.thread = threading.Thread(target=target, args=args)

    def start(self):
        self.thread.start()
        self.thread.join()


@pytest.fixture()
def sync_threads(monkeypatch, request):
    # these requests bump counters, so the test must get a re-seeded database
    request.node.add_marker(pytest.mark.writes)
    import alt2.video
    monkeypatch.setattr(alt2.video, "Thread", JoinedThread)


# --- embed ---------------------------------------------------------------------

def test_embed_renders_with_resolved_url(client):
    r = client.get("/embed/vid_ia_00002")
    assert r.status_code == 200
    assert IA_URL in r.get_data(as_text=True)


def test_embed_uses_own_storage_when_present(client):
    r = client.get("/embed/vid_ac_00003")
    assert "https://videos.test/vid_ac_00003/vid_ac_00003" in r.get_data(as_text=True)


@pytest.mark.parametrize("path", [
    "/embed/does_not_exist", "/embed/vid_gone_0004",
    f"/embed/vid_ia_00002?playlist=nope"])
def test_embed_404(client, path):
    assert client.get(path).status_code == 404


# --- video-sources -------------------------------------------------------------

def test_video_sources_json(client, sync_threads):
    r = client.get("/api/video-sources/vid_ia_00002", headers=UA)
    assert r.status_code == 200
    assert r.get_json()["video_url"] == IA_URL


def test_video_sources_next_in_channel(client, sync_threads):
    # newest archived video of Alpha: next is the older one
    r = client.get("/api/video-sources/vid_ac_00003", headers=UA)
    assert r.get_json()["next_watch_url"] == "/watch?v=vid_ia_00002"


def test_video_sources_next_in_playlist(client, sync_threads):
    r = client.get(f"/api/video-sources/vid_ac_00003?playlist={HASH}", headers=UA)
    assert r.get_json()["next_watch_url"] == f"/watch?v=vid_ia_00002&playlist={HASH}"


def test_video_sources_userlist_needs_login(client, sync_threads):
    r = client.get("/api/video-sources/vid_ac_00003?userlist=history", headers=UA)
    assert r.get_json()["next_watch_url"] is None


def test_video_sources_unknown_is_404(client):
    assert client.get("/api/video-sources/nope").status_code == 404


# --- ping-view counter -----------------------------------------------------------

def ac_views(sql, vid="vid_ia_00002"):
    return sql(f"select {schema.AC_VIEWS} from {schema.VIDEO_TABLE} "
               f"where extractor_data=:v", v=vid)[0][0]


@pytest.mark.writes
def test_ping_view_counts_once_per_visitor_per_day(client, sql, sync_threads):
    before = ac_views(sql) or 0
    for _ in range(3):
        assert client.post("/api/ping-view/vid_ia_00002",
                           headers=UA).status_code == 204
    assert ac_views(sql) == before + 1


@pytest.mark.writes
def test_ping_view_distinct_visitors_count_separately(client, sql, sync_threads):
    before = ac_views(sql) or 0
    client.post("/api/ping-view/vid_ia_00002", headers={"User-Agent": "a"})
    client.post("/api/ping-view/vid_ia_00002", headers={"User-Agent": "b"})
    assert ac_views(sql) == before + 2


@pytest.mark.writes
def test_ping_view_unknown_video_is_harmless(client, sql, sync_threads):
    assert client.post("/api/ping-view/nope", headers=UA).status_code == 204
    assert sql("select count(*) from counter") == [(0,)]


# --- play-next -------------------------------------------------------------------

def test_play_next_toggles_in_session(client):
    first = json.loads(client.get("/play-next").data)["playnext"]
    toggled = json.loads(client.post("/play-next", data="{}").data)["playnext"]
    assert toggled == (not first)
    assert json.loads(client.get("/play-next").data)["playnext"] == toggled


# --- watch page as a logged-in user ----------------------------------------------

@pytest.mark.writes
def test_watch_records_history_without_duplicates(user_client, sql):
    for v in ("vid_ia_00002", "vid_ac_00003", "vid_ia_00002"):
        assert user_client.get(f"/watch?v={v}").status_code == 200
    assert sql("select watched from altcen_user where username='alice'") \
        == [(["vid_ia_00002", "vid_ac_00003"],)]


def test_watch_offers_lists_the_video_is_not_in(user_client):
    body = user_client.get("/watch?v=vid_ia_00002").get_data(as_text=True)
    # alice's only playlist already holds this video
    assert "Alice list" not in body or "add_to_watchlater" in body


def test_watch_in_playlist_context(client):
    r = client.get(f"/watch?v=vid_ac_00003&playlist={HASH}")
    assert r.status_code == 200
    assert client.get("/watch?v=vid_ac_00003&playlist=nope").status_code == 404


@pytest.mark.writes
def test_watch_watchlater_context(client, sql):
    from sqlalchemy import text
    with client.application.app_context():
        from alt2.database import db_session
        db_session.execute(text("update altcen_user set watchlater="
                                "array['vid_ia_00002','vid_ac_00003'] "
                                "where username='alice'"))
        db_session.commit()
    login(client, "alice")
    assert client.get("/watch?v=vid_ac_00003&userlist=watchlater").status_code == 200
    r = client.get("/api/video-sources/vid_ac_00003?userlist=watchlater",
                   headers=UA)
    assert r.get_json()["next_watch_url"] == "/watch?v=vid_ia_00002&userlist=watchlater"


# --- search variants ---------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/search/latest?q=deleted", "/search/new?q=deleted",
    "/search/popular?q=deleted"])
def test_search_orderings_find_archived_video(client, path):
    r = client.get(path)
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Deleted, on IA" in body
    assert "Deleted, nowhere" not in body


def test_search_without_results(client):
    r = client.get("/search?q=zzzzzzzz")
    assert r.status_code == 200
    assert "Deleted, on IA" not in r.get_data(as_text=True)
