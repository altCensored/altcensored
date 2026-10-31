"""Channel and category listings, pagination, and the small static blueprints."""
import pytest

from tests import schema
from tests.conftest import flashes


# --- Pagination --------------------------------------------------------------------

def test_pagination_pages_and_neighbours():
    from alt2.pagination import Pagination
    p = Pagination(2, 24, 50)
    assert p.pages == 3 and p.has_prev and p.has_next
    assert not Pagination(1, 24, 24).has_next
    assert not Pagination(1, 24, 24).has_prev
    assert Pagination(1, 24, 0).pages == 0


def test_pagination_iter_pages_marks_gaps():
    from alt2.pagination import Pagination
    pages = list(Pagination(10, 10, 200).iter_pages())
    assert pages[0] == 1 and pages[-1] == 20
    assert None in pages and 10 in pages


# --- channels ----------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/channel/", "/channel/new", "/channel/popular", "/channel/deleted",
    "/channel/limited", "/channel/archived", "/channel/table",
    "/channel/table?data=data_deleted"])
def test_channel_listings_render(client, path):
    assert client.get(path).status_code == 200


def test_channel_index_lists_both_channels(client):
    body = client.get("/channel/").get_data(as_text=True)
    assert "Alpha Channel" in body and "Beta Channel" in body


def test_deleted_channel_listing_only_has_deleted(client):
    body = client.get("/channel/deleted").get_data(as_text=True)
    assert "Beta Channel" in body and "Alpha Channel" not in body


@pytest.mark.parametrize("path,expected", [
    ("/channel/data_all", 2), ("/channel/data_deleted", 1)])
def test_channel_datatables_endpoints(client, path, expected):
    r = client.get(f"{path}?draw=1&start=0&length=10")
    assert r.status_code == 200
    assert int(r.get_json()["recordsTotal"]) == expected


def test_channel_page_lists_only_archived_videos(client):
    body = client.get(f"/channel/{schema.ALPHA}").get_data(as_text=True)
    assert "Deleted, on IA" in body and "Deleted, on our storage" in body
    assert "Live video" not in body


def test_channel_popular_page(client):
    r = client.get(f"/channel/{schema.ALPHA}/popular")
    assert r.status_code == 200
    assert "Deleted, on IA" in r.get_data(as_text=True)


def test_channel_lookup_ignores_case(client):
    assert client.get(f"/channel/{schema.ALPHA.lower()}").status_code == 200


@pytest.mark.parametrize("path", [
    "/channel/UCnope", "/channel/UCnope/popular",
    f"/channel/{schema.ALPHA}/page/2", f"/channel/{schema.ALPHA}/popular/page/2"])
def test_channel_404s(client, path):
    assert client.get(path).status_code == 404


# --- categories --------------------------------------------------------------------

def test_category_index_lists_categories_that_have_videos(client):
    body = client.get("/category/").get_data(as_text=True)
    assert "Music" in body and "News" not in body


@pytest.mark.parametrize("suffix", ["", "/new", "/popular"])
def test_category_page_lists_its_videos(client, suffix):
    r = client.get(f"/category/1{suffix}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Deleted, on IA" in body and "Deleted, on our storage" not in body


@pytest.mark.parametrize("path", [
    "/category/abc", "/category/99999", "/category/99999/new",
    "/category/99999/popular", "/category/abc/new"])
def test_category_404s(client, path):
    assert client.get(path).status_code == 404


# --- listings with a second page ----------------------------------------------------

@pytest.mark.parametrize("path", [
    "/new/page/2", "/popular/page/2", "/latest/page/2", "/feed/page/2",
    "/channel/page/2", "/playlist/page/2"])
def test_empty_second_pages_do_not_crash(client, path):
    assert client.get(path).status_code in (200, 404)


# --- static blueprints -------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/about/", "/about/example", "/donate/", "/newsletter/", "/settings/"])
def test_static_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_theme_toggle_flips_between_light_and_dark(client):
    client.get("/")                       # creates session['theme']
    with client.session_transaction() as s:
        before = s["theme"]
    client.post("/theme/toggle")
    with client.session_transaction() as s:
        assert s["theme"] == ("dark" if before == "light" else "light")
    client.post("/theme/toggle")
    with client.session_transaction() as s:
        assert s["theme"] == before
