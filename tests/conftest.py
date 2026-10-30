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
    os.environ.setdefault("ALTC_SECRET_KEY", "test-secret-key")
    os.environ.setdefault("ALTC_LOGGEDIN_SECRET", "test-loggedin-secret")
    os.environ.setdefault("RANDOM_VALUE", "testvalue")
    os.environ.setdefault("CACHE_REDIS_HOST", "localhost")


@pytest.fixture(scope="session")
def engine():
    from altcen_models.db import Base
    from alt2 import models  # noqa: F401  registers every table on Base
    eng = create_engine(TEST_URL)
    from tests import seed
    with eng.begin() as conn:
        for mv in reversed(seed.MATVIEWS):  # a leftover may be a table or a view
            conn.exec_driver_sql(
                f"DO $$ BEGIN "
                f"IF to_regclass('{mv}') IS NOT NULL THEN "
                f"IF (SELECT relkind FROM pg_class WHERE oid = '{mv}'::regclass) = 'm' "
                f"THEN DROP MATERIALIZED VIEW {mv}; ELSE DROP TABLE {mv}; END IF; "
                f"END IF; END $$")
    Base.metadata.drop_all(eng)
    # the mv_* ORM models are only mappings; the real views come from prod's DDL
    real = [t for n, t in Base.metadata.tables.items() if not n.startswith("mv_")]
    Base.metadata.create_all(eng, tables=real)
    seed.create_matviews(eng)
    seed.load(eng)
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
