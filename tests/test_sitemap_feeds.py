"""Sitemaps and Atom/RSS feeds: well-formed XML that lists the seeded data.
Both are cached by nginx, so the app must never set the loggedin cookie there."""
import xml.etree.ElementTree as ET

import pytest

from tests import schema
from tests.conftest import login


def parse(response):
    return ET.fromstring(response.data)


def texts(root, tag):
    return [e.text for e in root.iter() if e.tag.split("}")[-1] == tag]


# --- sitemaps --------------------------------------------------------------------

def test_sitemap_index_lists_the_sub_sitemaps(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200 and r.mimetype == "application/xml"
    locs = texts(parse(r), "loc")
    assert any("sitemap-videos-1.xml" in u for u in locs)
    assert any("sitemap-channels.xml" in u for u in locs)
    assert any("sitemap-static.xml" in u for u in locs)


def test_sitemap_videos_lists_archived_videos_only(client):
    root = parse(client.get("/sitemap-videos-1.xml"))
    urls = " ".join(texts(root, "loc"))
    assert "vid_ia_00002" in urls and "vid_ac_00003" in urls
    assert "vid_live_0001" not in urls and "vid_gone_0004" not in urls


def test_sitemap_videos_past_the_end_is_empty(client):
    r = client.get("/sitemap-videos-99.xml")
    assert r.status_code == 200
    assert texts(parse(r), "loc") == []


def test_sitemap_channels_lists_every_channel(client):
    urls = " ".join(texts(parse(client.get("/sitemap-channels.xml")), "loc"))
    assert schema.ALPHA in urls and schema.BETA in urls


def test_sitemap_static_lists_categories(client):
    r = client.get("/sitemap-static.xml")
    assert r.status_code == 200
    assert len(texts(parse(r), "loc")) >= 2


@pytest.mark.parametrize("path", ["/sitemap.xml", "/sitemap-channels.xml",
                                  "/feed", "/channel/deleted/feed"])
def test_cached_paths_never_set_loggedin_cookie(user_client, path):
    r = user_client.get(path)
    assert r.status_code == 200
    assert not any(c.startswith("loggedin=") for c in r.headers.getlist("Set-Cookie"))


def test_html_pages_refresh_loggedin_cookie_for_users(client):
    login(client, "alice")
    client.delete_cookie("loggedin")
    r = client.get("/about/")
    assert any(c.startswith("loggedin=") for c in r.headers.getlist("Set-Cookie"))


# --- feeds -----------------------------------------------------------------------

FEEDS = ["/feed", "/channel/feed", "/channel/deleted/feed",
         f"/channel/{schema.ALPHA}/feed"]


@pytest.mark.parametrize("path", FEEDS)
def test_feed_is_well_formed_xml(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "xml" in r.mimetype
    parse(r)


def test_video_feed_lists_archived_videos(client):
    body = client.get("/feed").get_data(as_text=True)
    assert "Deleted, on IA" in body and "Deleted, on our storage" in body
    assert "Live video" not in body


def test_channel_feed_lists_that_channels_videos(client):
    body = client.get(f"/channel/{schema.ALPHA}/feed").get_data(as_text=True)
    assert "Deleted, on IA" in body
    assert "Deleted, nowhere" not in body


def test_deleted_channel_feed_lists_the_deleted_channel(client):
    body = client.get("/channel/deleted/feed").get_data(as_text=True)
    assert "Beta Channel" in body and "Alpha Channel" not in body


def test_unknown_channel_feed_is_an_empty_feed_not_a_404(client):
    r = client.get("/channel/UCnope/feed")
    assert r.status_code == 200
    assert not [e for e in parse(r).iter() if e.tag == "item"]
