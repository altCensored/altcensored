"""Page 2 and beyond of the paginated routes.

The seed is too small for a second page at the real page size (24), so each test sets
the module's PER_PAGE to 1. The two archived videos and the two channels then split
over pages 1 and 2, and page 3 is past the end."""
import pytest

from tests.conftest import login
from tests.test_user import set_array

VIDEOS = ("Deleted, on IA", "Deleted, on our storage")
CHANNELS = ("Alpha Channel", "Beta Channel")


def shown(client, path, titles):
    r = client.get(path)
    assert r.status_code == 200, path
    body = r.get_data(as_text=True)
    return {t for t in titles if t in body}


def assert_split(client, path, titles, query=""):
    """Page 1 and page 2 each show one of the titles, together all of them."""
    first = shown(client, path + query, titles)
    second = shown(client, path + "/page/2" + query, titles)
    assert len(first) == 1 and len(second) == 1, (first, second)
    assert first | second == set(titles)


# --- search ------------------------------------------------------------------------

@pytest.mark.parametrize("prefix", ["/search", "/search/latest", "/search/new", "/search/popular"])
def test_search_second_page_has_the_other_result(client, monkeypatch, prefix):
    monkeypatch.setattr("alt2.video.PER_PAGE", 1)
    assert_split(client, prefix, VIDEOS, "?q=deleted")
    assert client.get(f"{prefix}/page/3?q=deleted").status_code == 404


# --- channel listings --------------------------------------------------------------

@pytest.mark.parametrize("prefix", ["/channel/archived", "/channel/limited"])
def test_channel_listing_splits_over_two_pages(client, monkeypatch, prefix):
    monkeypatch.setattr("alt2.channel.PER_PAGE", 1)
    assert_split(client, prefix, CHANNELS)
    assert client.get(f"{prefix}/page/3").status_code == 404


@pytest.mark.parametrize("path", ["/channel/deleted/page/2", "/channel/deleted/feed/page/2"])
def test_deleted_channels_have_no_second_page(client, monkeypatch, path):
    """Only Beta Channel is deleted on YouTube, so even at one per page there is no page 2."""
    monkeypatch.setattr("alt2.channel.PER_PAGE", 1)
    assert client.get(path).status_code == 404


def test_deleted_channels_first_page_lists_beta(client, monkeypatch):
    monkeypatch.setattr("alt2.channel.PER_PAGE", 1)
    assert shown(client, "/channel/deleted", CHANNELS) == {"Beta Channel"}


# --- history and watch later -------------------------------------------------------

@pytest.mark.writes
@pytest.mark.parametrize("column,route", [("watched", "history"), ("watchlater", "watchlater")])
def test_own_lists_split_over_pages_newest_first(client, monkeypatch, column, route):
    monkeypatch.setattr("alt2.user.PER_PAGE", 1)
    set_array(client, column, ["vid_ia_00002", "vid_ac_00003"])   # oldest first
    login(client, "alice")
    # the last entry added is listed first
    assert shown(client, f"/user/{route}", VIDEOS) == {"Deleted, on our storage"}
    assert shown(client, f"/user/{route}/page/2", VIDEOS) == {"Deleted, on IA"}
    # past the end must not be a server error
    assert client.get(f"/user/{route}/page/3").status_code < 500
