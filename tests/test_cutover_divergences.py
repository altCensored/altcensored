"""Behaviour that differs between the legacy and ytac schemas by design, pinned
so a change on either side is noticed.

Legacy ``exists_ia`` is tri-state (NULL = unknown, so the resolver asks archive.org);
ytac's ``ia_exists`` is NOT NULL, so the same video is simply "not on IA"."""
import pytest
from sqlalchemy import text

from tests import schema, seed

IA_URL = "https://ia.test/lookup"
VID = "vid_ac_00003"        # deleted, own storage only: exists_ia is False


@pytest.fixture()
def resolver(monkeypatch):
    """S3 says the object is missing; archive.org lookups are recorded."""
    import alt2.video
    lookups = []
    monkeypatch.setattr(alt2.video, "check_ac_object_exists", lambda v: False)
    monkeypatch.setattr(alt2.video, "get_ia_item",
                        lambda v: lookups.append(v) or IA_URL)
    return lookups


def test_known_not_on_ia_is_unavailable_without_a_lookup(client, resolver):
    body = client.get(f"/embed/{VID}").get_data(as_text=True)
    assert "unavailable/unavailable" in body
    assert resolver == []


@pytest.mark.legacy
@pytest.mark.writes
def test_unknown_ia_status_asks_archive_org_on_legacy(client, engine, resolver):
    with engine.begin() as c:
        c.execute(text("update entity set exists_ia = NULL "
                       "where extractor_data = :v"), {"v": VID})
    seed.refresh_matviews(engine)
    body = client.get(f"/embed/{VID}").get_data(as_text=True)
    assert IA_URL in body
    assert resolver == [VID]


@pytest.mark.ytac
def test_unknown_ia_status_cannot_exist_on_ytac(engine):
    # NOT NULL: the 10 legacy rows with NULL become False at migration time
    with engine.connect() as c:
        nullable = c.execute(text(
            "select is_nullable from information_schema.columns "
            "where table_name='video' and column_name='ia_exists'")).scalar()
    assert nullable == "NO"


def test_channel_feed_always_has_a_thumbnail_image(client):
    # channel_index.xml reads ytc_thumbnailurl on master and the renamed column on
    # the cutover; the seed has no thumbnail, so the error image must show
    body = client.get("/channel/feed").get_data(as_text=True)
    assert "<img" in body and 'src=""' not in body
    assert schema.ALPHA in body
