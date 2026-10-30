"""Test harness: real app, real PostgreSQL, small seeded dataset.

Set ALTC_TEST_DATABASE_URL to a *dedicated* database whose name ends in
``_test``. The suite drops and recreates every table in it, so it refuses
anything else. Use the explicit ``postgresql+psycopg2://`` form.

Redis is not used: the cache is a NullCache and the limiter is in memory,
so a run never touches the Redis DB 1 that a deployed app on the same host
uses.
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

TEST_URL = os.environ.get("ALTC_TEST_DATABASE_URL")


def pytest_configure(config):
    if not TEST_URL:
        raise pytest.UsageError("ALTC_TEST_DATABASE_URL is not set")
    name = make_url(TEST_URL).database or ""
    if not name.endswith("_test"):
        raise pytest.UsageError(
            f"refusing to run: database {name!r} does not end in '_test'")
    # config.py reads these at import time, so set them before alt2 loads
    os.environ["ALTC_DATABASE_URL"] = TEST_URL
    os.environ["ALTC_SECRET_KEY"] = "test-secret-key"
    os.environ["ALTC_LOGGEDIN_SECRET"] = "test-loggedin-secret"
    os.environ["RANDOM_VALUE"] = "testvalue"
    os.environ["CACHE_REDIS_HOST"] = "localhost"
    os.environ["VIDEOSERVER_URL"] = "https://videos.test/"


@pytest.fixture(scope="session")
def engine():
    from alt2 import models  # noqa: F401  registers every table on Base
    eng = create_engine(TEST_URL)
    from tests import seed
    seed.setup(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def app(engine):
    from alt2 import create_app
    from alt2.cache import cache
    cache.config["CACHE_TYPE"] = "NullCache"
    return create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        "RATELIMIT_STORAGE_URI": "memory://",
        "SERVER_NAME": None,
    })


@pytest.fixture()
def client(app):
    # the app redirects to https unless told the request already was
    c = app.test_client()
    c.environ_base["HTTP_X_FORWARDED_PROTO"] = "https"
    c.environ_base["HTTP_HOST"] = "altcensored.com"
    return c


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """The player logic calls S3 and archive.org. Fail loudly instead of going
    out; a test that needs either stubs it (monkeypatch.setattr again)."""
    def boom(*a, **k):
        raise AssertionError("unexpected network call in test")
    import alt2.video
    monkeypatch.setattr(alt2.video, "check_ac_object_exists", boom)
    monkeypatch.setattr(alt2.video, "get_ia_item", boom)
