"""Playlist pages and the write routes behind the watch-page buttons."""
import pytest

from tests.conftest import flashes
from tests.seed import PLAYLIST

HASH = PLAYLIST["hashid"]


def vids(sql):
    return sql("select videos from playlist where hashid=:h", h=HASH)[0][0]


def test_index_and_popular_render(client):
    assert client.get("/playlist/").status_code == 200
    assert client.get("/playlist/popular").status_code == 200


def test_item_lists_its_videos(client):
    r = client.get(f"/playlist/{HASH}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Alice list" in body
    assert "Deleted, on IA" in body
    assert "Deleted, on our storage" in body
    assert "Live video" not in body


def test_item_unknown_is_404(client):
    assert client.get("/playlist/nope").status_code == 404


@pytest.mark.writes
def test_item_counts_one_view_per_day(client, sql):
    client.get(f"/playlist/{HASH}")
    client.get(f"/playlist/{HASH}")
    assert sql("select view_counter from playlist where hashid=:h", h=HASH) == [(1,)]


@pytest.mark.writes
def test_item_repairs_dead_featured_video(client, sql):
    sql_text = "update playlist set featured_video_id='gone_missing' where hashid=:h"
    from sqlalchemy import text
    with client.application.app_context():
        from alt2.database import db_session
        db_session.execute(text(sql_text), {"h": HASH})
        db_session.commit()
    assert client.get(f"/playlist/{HASH}").status_code == 200
    assert sql("select featured_video_id from playlist where hashid=:h",
               h=HASH) == [("vid_ia_00002",)]


# --- create / edit / delete -------------------------------------------------

@pytest.mark.writes
def test_create_playlist(user_client, sql):
    r = user_client.post("/playlist/create", data=dict(
        title="Brand new", description="d", public="True"))
    assert r.status_code == 302
    assert r.headers["Location"].startswith("/playlist/AC")
    assert sql("select user_id, video_count, public from playlist "
               "where title='Brand new'") == [(2, 0, True)]


@pytest.mark.writes
def test_create_rejects_duplicate_title(user_client, sql):
    r = user_client.post("/playlist/create", data=dict(
        title="Alice list", description="", public="True"))
    assert r.headers["Location"].endswith("/playlist/create")
    assert sql("select count(*) from playlist") == [(1,)]
    assert flashes(user_client)[-1][0] == "error"


@pytest.mark.writes
def test_edit_playlist_owner_only(client, sql):
    from tests.conftest import login
    pid = sql("select id from playlist")[0][0]
    login(client, "admin")
    assert client.get(f"/playlist/edit/{pid}").status_code == 403
    client.get("/auth/logout")
    login(client, "alice")
    r = client.post(f"/playlist/edit/{pid}", data=dict(
        title="Renamed", description="x", public="False"))
    assert r.status_code == 302
    assert sql("select title, public from playlist") == [("Renamed", False)]


@pytest.mark.writes
def test_delete_playlist(user_client, sql):
    pid = sql("select id from playlist")[0][0]
    assert user_client.get(f"/playlist/delete/{pid}").status_code == 200
    user_client.post(f"/playlist/delete/{pid}", data=dict(submitvalue="no"))
    assert sql("select count(*) from playlist") == [(1,)]
    user_client.post(f"/playlist/delete/{pid}", data=dict(submitvalue="yes"))
    assert sql("select count(*) from playlist") == [(0,)]


def test_edit_and_delete_unknown_are_404(user_client):
    assert user_client.get("/playlist/edit/99999").status_code == 404
    assert user_client.get("/playlist/delete/99999").status_code == 404


# --- add / remove videos ----------------------------------------------------

@pytest.mark.writes
def test_add_video_form(user_client, sql):
    r = user_client.post("/playlist/add_video_playlist", data=dict(
        v="vid_live_0001", playlist_title="Alice list"))
    assert r.status_code == 302
    assert vids(sql)[-1] == "vid_live_0001"
    assert sql("select video_count from playlist") == [(3,)]


@pytest.mark.writes
def test_add_video_twice_is_idempotent(user_client, sql):
    for _ in range(2):
        user_client.post("/playlist/add_video_playlist", data=dict(
            v="vid_ia_00002", playlist_title="Alice list"))
    assert vids(sql).count("vid_ia_00002") == 1


@pytest.mark.writes
def test_add_to_watchlater(user_client, sql):
    user_client.post("/playlist/add_video_playlist", data=dict(
        v="vid_live_0001", playlist_title="add_to_watchlater"))
    assert sql("select watchlater from altcen_user where username='alice'") \
        == [(["vid_live_0001"],)]


@pytest.mark.writes
def test_add_video_list_full(user_client, sql, monkeypatch):
    import alt2.util
    monkeypatch.setattr(alt2.util, "MAX_LIST_VIDEOS", 2)
    user_client.post("/playlist/add_video_playlist", data=dict(
        v="vid_live_0001", playlist_title="Alice list"))
    assert len(vids(sql)) == 2
    assert ("error", "List is full") in flashes(user_client)


def test_add_video_rejects_bad_id_and_unknown_list(user_client):
    r = user_client.post("/playlist/add_video_playlist", data=dict(
        v="bad id!", playlist_title="Alice list"))
    assert r.status_code == 400
    r = user_client.post("/playlist/add_video_playlist", data=dict(
        v="vid_live_0001", playlist_title="no such list"))
    assert r.status_code == 404


def test_add_video_requires_login(client):
    r = client.post("/playlist/add_video_playlist", data=dict(
        v="vid_live_0001", playlist_title="Alice list"))
    assert r.status_code == 302


@pytest.mark.writes
def test_add_video_json(user_client, sql):
    r = user_client.post("/playlist/add_video_playlist_post",
                         json=dict(v="vid_live_0001", p=HASH))
    assert r.status_code == 200 and r.get_json() == {"v": "vid_live_0001"}
    assert "vid_live_0001" in vids(sql)


@pytest.mark.parametrize("payload,code", [
    ({"v": "vid_live_0001"}, 400), ({"v": "bad id", "p": HASH}, 400),
    ({"v": "vid_live_0001", "p": "nope"}, 404)])
def test_add_video_json_errors(user_client, payload, code):
    assert user_client.post("/playlist/add_video_playlist_post",
                            json=payload).status_code == code


def test_add_video_json_not_owner(client):
    from tests.conftest import login
    login(client, "admin")
    r = client.post("/playlist/add_video_playlist_post",
                    json=dict(v="vid_live_0001", p=HASH))
    assert r.status_code == 403


@pytest.mark.writes
def test_add_video_json_full(user_client, monkeypatch):
    import alt2.util
    monkeypatch.setattr(alt2.util, "MAX_LIST_VIDEOS", 2)
    r = user_client.post("/playlist/add_video_playlist_post",
                         json=dict(v="vid_live_0001", p=HASH))
    assert r.status_code == 409


@pytest.mark.writes
def test_remove_video_updates_count_and_featured(user_client, sql):
    from sqlalchemy import text
    with user_client.application.app_context():
        from alt2.database import db_session
        db_session.execute(text("update playlist set featured_video_id="
                                "'vid_ia_00002'"))
        db_session.commit()
    r = user_client.post("/playlist/remove_video_playlist", data=dict(
        playlist=HASH, v="vid_ia_00002"))
    assert r.status_code == 302
    assert vids(sql) == ["vid_ac_00003"]
    assert sql("select video_count, featured_video_id from playlist") \
        == [(1, "vid_ac_00003")]


def test_remove_video_not_owner(client):
    from tests.conftest import login
    login(client, "admin")
    r = client.post("/playlist/remove_video_playlist",
                    data=dict(playlist=HASH, v="vid_ia_00002"))
    assert r.status_code == 403
