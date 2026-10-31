"""What the main fixtures switch off: the Redis-backed cache (here an in-process
SimpleCache) and the rate limiter (here in-memory). A separate app is built so
the rest of the suite keeps running with both disabled.

The cache and limiter objects are module globals shared by every app, so the
fixture builds the app with SimpleCache, then puts the config back and turns the
limiter off again after each test."""
import pytest

from tests import schema


@pytest.fixture(scope="session")
def strict_app(engine):
    from alt2 import create_app
    from alt2.cache import cache
    previous = cache.config["CACHE_TYPE"]
    cache.config["CACHE_TYPE"] = "SimpleCache"
    try:
        return create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": True,
            "RATELIMIT_STORAGE_URI": "memory://",
        })
    finally:
        cache.config["CACHE_TYPE"] = previous


@pytest.fixture()
def strict(strict_app):
    from alt2 import limiter
    from alt2.cache import cache
    limiter.enabled = True
    limiter.reset()
    with strict_app.app_context():
        cache.clear()
    c = strict_app.test_client()
    c.environ_base["HTTP_X_FORWARDED_PROTO"] = "https"
    c.environ_base["HTTP_HOST"] = "altcensored.com"
    yield c
    limiter.reset()
    limiter.enabled = False


# --- rate limits -----------------------------------------------------------------

def bad_login(client):
    return client.post("/auth/login", data=dict(username="alice", password="no"))


def test_login_is_limited_to_five_a_minute(strict):
    codes = [bad_login(strict).status_code for _ in range(6)]
    assert codes[:5] == [302] * 5
    assert codes[5] == 429


def login_from(client, forwarded):
    return client.post("/auth/login", data=dict(username="alice", password="no"),
                       headers={"X-Forwarded-For": forwarded})


def test_each_visitor_has_their_own_login_budget(strict):
    # behind nginx remote_addr is the same for everyone; the key is the address
    # nginx appended to X-Forwarded-For
    for _ in range(6):
        login_from(strict, "203.0.113.1")
    assert login_from(strict, "203.0.113.1").status_code == 429
    assert login_from(strict, "203.0.113.2").status_code == 302


def test_a_forged_first_forwarded_entry_does_not_buy_a_new_budget(strict):
    # the client controls the first entries; only the last one is nginx's
    codes = [login_from(strict, f"198.51.100.{i}, 203.0.113.9").status_code
             for i in range(6)]
    assert codes[:5] == [302] * 5 and codes[5] == 429


def test_the_limit_page_is_our_error_page_not_bare_text(strict):
    for _ in range(5):
        bad_login(strict)
    r = bad_login(strict)
    assert r.status_code == 429
    body = r.get_data(as_text=True)
    assert "<h1>Too many requests" in body and "Too Many Requests -" not in body
    assert r.headers["Retry-After"] == "60"


def test_limit_applies_per_route(strict):
    for _ in range(6):
        bad_login(strict)
    assert strict.get("/about/").status_code == 200
    r = strict.post("/auth/reset_password_request", data=dict(identity="nobody"))
    assert r.status_code == 302            # its own budget is untouched


def test_password_reset_request_is_limited_to_five_a_minute(strict):
    codes = [strict.post("/auth/reset_password_request",
                         data=dict(identity="nobody")).status_code
             for _ in range(6)]
    assert codes[5] == 429 and 429 not in codes[:5]


def test_a_blocked_login_cannot_succeed_with_the_right_password(strict):
    from tests.seed import PASSWORD
    for _ in range(5):
        bad_login(strict)
    r = strict.post("/auth/login", data=dict(username="alice", password=PASSWORD))
    assert r.status_code == 429
    with strict.session_transaction() as s:
        assert not s.get("user")


def test_the_main_fixtures_still_run_unlimited(client):
    from alt2 import limiter
    assert limiter.enabled is False
    for _ in range(8):
        assert client.post("/auth/login", data=dict(
            username="alice", password="no")).status_code == 302


# --- cache -----------------------------------------------------------------------

def rename_video(sql_engine, title, vid="vid_ia_00002"):
    from sqlalchemy import text
    from tests import seed
    with sql_engine.begin() as c:
        c.execute(text(f"update {schema.VIDEO_TABLE} set title=:t "
                       "where extractor_data=:v"), {"t": title, "v": vid})
    seed.refresh_matviews(sql_engine)


@pytest.mark.writes
def test_listings_are_served_from_cache_until_cleared(strict, strict_app, engine):
    from alt2.cache import cache
    assert "Deleted, on IA" in strict.get("/").get_data(as_text=True)
    rename_video(engine, "Renamed in the database")
    stale = strict.get("/").get_data(as_text=True)
    assert "Deleted, on IA" in stale and "Renamed in the database" not in stale
    with strict_app.app_context():
        cache.clear()
    assert "Renamed in the database" in strict.get("/").get_data(as_text=True)


@pytest.mark.writes
def test_watch_page_reads_the_view_directly(strict, engine, monkeypatch):
    import alt2.video
    monkeypatch.setattr(alt2.video, "check_ac_object_exists", lambda vid: True)
    assert "Deleted, on our storage" in strict.get(
        "/watch?v=vid_ac_00003").get_data(as_text=True)
    rename_video(engine, "Fresh title", "vid_ac_00003")
    assert "Fresh title" in strict.get(
        "/watch?v=vid_ac_00003").get_data(as_text=True)


def test_sitemap_pages_are_cached_for_a_day(strict, strict_app):
    strict.get("/sitemap-channels.xml")
    from alt2.cache import cache
    with strict_app.app_context():
        assert cache.get("sitemap_channels") is not None
