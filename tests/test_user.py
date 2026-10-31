"""Public user pages, history and watch-later management."""
import pytest

from tests import schema
from tests.conftest import flashes, login


def set_array(client, column, values):
    """Put values straight into alice's history or watch-later array."""
    from sqlalchemy import text
    with client.application.app_context():
        from alt2.database import db_session
        db_session.execute(
            text(f"update altcen_user set {column}=:v where username='alice'"),
            {"v": values})
        db_session.commit()


def array(sql, column):
    return sql(f"select {column} from altcen_user where username='alice'")[0][0]


# --- public pages ------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/user/", "/user/popular"])
def test_user_listings_render(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "alice" in r.get_data(as_text=True)


def test_user_listing_second_page_is_404(client):
    assert client.get("/user/page/2").status_code == 404


@pytest.mark.writes
def test_profile_page_and_view_counter(client, sql):
    assert client.get("/user/Alice").status_code == 200    # lookup ignores case
    client.get("/user/Alice")           # same visitor, same day: counted once
    assert sql("select view_counter from altcen_user where username='alice'") \
        == [(1,)]


def test_profile_hides_playlists_without_featured_video(client):
    assert "Alice list" not in client.get("/user/alice").get_data(as_text=True)


def test_owner_sees_own_public_playlists(user_client):
    assert "Alice list" in user_client.get("/user/alice").get_data(as_text=True)


def test_unknown_profile_redirects_with_flash(client):
    r = client.get("/user/nobody")
    assert r.status_code == 302
    assert ("error", "User unknown") in flashes(client)


# --- history -----------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/user/history", "/user/watchlater", "/user/playlist",
    "/user/clear_history", "/user/clear_watchlater"])
def test_private_pages_need_login(client, path):
    r = client.get(path)
    assert r.status_code == 302
    assert flashes(client) == []


def test_empty_history_and_watchlater_redirect(user_client):
    for path in ("/user/history", "/user/watchlater"):
        assert user_client.get(path).status_code == 302
    assert ("success", "History Empty") in flashes(user_client)


@pytest.mark.writes
def test_history_lists_watched_videos_newest_first(client):
    set_array(client, "watched", ["vid_ia_00002", "vid_ac_00003"])
    login(client, "alice")
    body = client.get("/user/history").get_data(as_text=True)
    assert body.index("Deleted, on our storage") < body.index("Deleted, on IA")


@pytest.mark.writes
def test_remove_video_from_history(client, sql):
    set_array(client, "watched", ["vid_ia_00002", "vid_ac_00003"])
    login(client, "alice")
    r = client.post("/user/remove_video_history", data=dict(v="vid_ia_00002"))
    assert r.status_code == 302
    assert array(sql, "watched") == ["vid_ac_00003"]


@pytest.mark.writes
def test_clear_history_asks_first(client, sql):
    set_array(client, "watched", ["vid_ia_00002"])
    login(client, "alice")
    assert client.get("/user/clear_history").status_code == 200
    client.post("/user/clear_history", data=dict(submitvalue="no"))
    assert array(sql, "watched") == ["vid_ia_00002"]
    client.post("/user/clear_history", data=dict(submitvalue="yes"))
    assert array(sql, "watched") == []


# --- watch later -------------------------------------------------------------------

@pytest.mark.writes
def test_add_and_list_watchlater(user_client, sql):
    r = user_client.post("/user/add_video_watchlater", data=dict(v="vid_ia_00002"))
    assert r.status_code == 302
    assert array(sql, "watchlater") == ["vid_ia_00002"]
    assert "Deleted, on IA" in user_client.get("/user/watchlater").get_data(as_text=True)


@pytest.mark.writes
def test_add_watchlater_twice_keeps_one(user_client, sql):
    for _ in range(2):
        user_client.post("/user/add_video_watchlater", data=dict(v="vid_ia_00002"))
    assert array(sql, "watchlater") == ["vid_ia_00002"]


@pytest.mark.writes
def test_add_watchlater_list_full(user_client, sql, monkeypatch):
    import alt2.util
    monkeypatch.setattr(alt2.util, "MAX_LIST_VIDEOS", 1)
    user_client.post("/user/add_video_watchlater", data=dict(v="vid_ia_00002"))
    user_client.post("/user/add_video_watchlater", data=dict(v="vid_ac_00003"))
    assert array(sql, "watchlater") == ["vid_ia_00002"]
    assert ("error", "List is full") in flashes(user_client)


def test_add_watchlater_rejects_bad_id(user_client):
    assert user_client.post("/user/add_video_watchlater",
                            data=dict(v="bad id!")).status_code == 400


@pytest.mark.writes
def test_add_watchlater_json(user_client, sql):
    r = user_client.post("/user/add_video_watchlater_post",
                         json=dict(v="vid_ac_00003"))
    assert r.get_json() == {"v": "vid_ac_00003"}
    assert array(sql, "watchlater") == ["vid_ac_00003"]
    assert user_client.post("/user/add_video_watchlater_post",
                            json=dict(v="bad id!")).status_code == 400


@pytest.mark.writes
def test_add_watchlater_json_full(user_client, monkeypatch):
    import alt2.util
    monkeypatch.setattr(alt2.util, "MAX_LIST_VIDEOS", 1)
    user_client.post("/user/add_video_watchlater_post", json=dict(v="vid_ia_00002"))
    r = user_client.post("/user/add_video_watchlater_post", json=dict(v="vid_ac_00003"))
    assert r.status_code == 409


@pytest.mark.writes
def test_remove_and_clear_watchlater(client, sql):
    set_array(client, "watchlater", ["vid_ia_00002", "vid_ac_00003"])
    login(client, "alice")
    client.post("/user/remove_video_watchlater", data=dict(v="vid_ia_00002"))
    assert array(sql, "watchlater") == ["vid_ac_00003"]
    client.post("/user/clear_watchlater", data=dict(submitvalue="no"))
    assert array(sql, "watchlater") == ["vid_ac_00003"]
    client.post("/user/clear_watchlater", data=dict(submitvalue="yes"))
    assert array(sql, "watchlater") == []


def test_own_playlists_page(user_client):
    r = user_client.get("/user/playlist")
    assert r.status_code == 200
    assert "Alice list" in r.get_data(as_text=True)


# --- deleting the account ----------------------------------------------------------

@pytest.mark.writes
def test_delete_account_needs_confirmation(user_client, sql):
    assert user_client.get("/auth/delete").status_code == 200
    user_client.post("/auth/delete", data=dict(submitvalue="no"))
    assert sql("select count(*) from altcen_user where username='alice'") == [(1,)]


@pytest.mark.writes
def test_delete_account_without_playlists(client, sql):
    login(client, "newbie")
    client.post("/auth/delete", data=dict(submitvalue="yes"))
    assert sql("select count(*) from altcen_user where username='newbie'") == [(0,)]


# alice owns a playlist. Legacy used to fail here because the ORM tried to null
# the foreign key on User.mv_playlist (a materialized view); /auth/delete now
# issues a bulk DELETE and the database's ON DELETE CASCADE removes the
# playlists. ytac's schema has no such rule until v28 (pin move pending), so
# it stays a strict xfail there; drop the marker when the pin moves.
@pytest.mark.xfail(schema.BACKEND != "legacy", strict=True,
                   reason="ytac: no ON DELETE CASCADE until schema v28")
@pytest.mark.writes
def test_delete_account_removes_the_user_and_its_playlists(user_client, sql):
    r = user_client.post("/auth/delete", data=dict(submitvalue="yes"))
    assert r.status_code == 302
    assert sql("select count(*) from altcen_user where username='alice'") == [(0,)]
    assert sql("select count(*) from playlist") == [(0,)]
