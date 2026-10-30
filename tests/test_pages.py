"""Smoke tests: the main pages render and show the seeded data."""
import pytest

ALPHA = "UCaaaaaaaaaaaaaaaaaaaaaa"
BETA = "UCbbbbbbbbbbbbbbbbbbbbbb"


@pytest.mark.parametrize("path", [
    "/", "/new", "/popular", "/latest", "/feed",
    "/channel/", "/channel/deleted", f"/channel/{ALPHA}", f"/channel/{BETA}",
    "/category/", "/about/", "/search?q=deleted",
])
def test_page_renders(client, path):
    assert client.get(path).status_code == 200


def test_home_lists_archived_deleted_videos_only(client):
    html = client.get("/").get_data(as_text=True)
    assert "Deleted, on IA" in html
    assert "Deleted, on our storage" in html
    # live, or deleted but archived nowhere: prod's mv_video excludes both
    assert "Live video" not in html
    assert "Deleted, nowhere" not in html


def test_channel_page_shows_channel(client):
    html = client.get(f"/channel/{ALPHA}").get_data(as_text=True)
    assert "Alpha Channel" in html


def test_search_finds_by_title(client):
    html = client.get("/search?q=storage").get_data(as_text=True)
    assert "Deleted, on our storage" in html
    assert "Deleted, on IA" not in html


def test_watch_page_renders_for_archived_video(client, monkeypatch):
    import alt2.video
    monkeypatch.setattr(alt2.video, "get_ia_item", lambda vid: "https://ia.test/x")
    r = client.get("/watch?v=vid_ia_00002")
    assert r.status_code == 200
    assert "Deleted, on IA" in r.get_data(as_text=True)


@pytest.mark.parametrize("path", [
    "/watch",                       # no id
    "/watch?v=vid_gone_0004",       # not in mv_video
    "/watch?v=does_not_exist",
])
def test_watch_404(client, path):
    assert client.get(path).status_code == 404
