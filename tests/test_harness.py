"""Proves the harness itself: seed loaded, app boots, a page renders."""
from sqlalchemy import text


def test_seed_counts(engine):
    with engine.connect() as c:
        n = lambda t: c.execute(text(f"select count(*) from {t}")).scalar()
        assert n("source") == 2
        assert n("video") == 4
        assert n("content") == 4
        # prod's view keeps deleted videos that are archived somewhere
        assert n("mv_video") == 2
        assert n("mv_channel") == 2


def test_home_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200


def test_seed_accounts(engine):
    with engine.connect() as c:
        n = lambda t: c.execute(text(f"select count(*) from {t}")).scalar()
        assert n("altcen_user") == 3
        assert n("category") == 2
        assert n("playlist") == 1
