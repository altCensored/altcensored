"""Internet Archive lookups. archive.org is never contacted: get_item is
replaced with a fake item carrying canned metadata."""
from types import SimpleNamespace

import pytest
import requests

from tests import schema

VID = "vid_live_0001"     # a seeded video with no IA data yet


def ia_item(files, identifier=f"youtube-{VID}"):
    return SimpleNamespace(item_metadata={"files": files} if files is not None else {},
                           identifier=identifier)


def f(name, source="original", fmt=None):
    d = {"name": name, "source": source}
    if fmt:
        d["format"] = fmt
    return d


@pytest.fixture()
def fake_get_item(monkeypatch):
    import alt2.services.archive as archive

    def install(item=None, exc=None):
        def get_item(identifier):
            if exc:
                raise exc
            return item
        monkeypatch.setattr(archive, "get_item", get_item)
    return install


def run_get_ia_item(client, vid=VID):
    from alt2.services.archive import get_ia_item
    with client.application.test_request_context():
        return get_ia_item(vid)


def row(sql):
    return sql(f"select videofile, {schema.IA_THUMB}, {schema.IA_NOVIDEO} "
               f"from {schema.VIDEO_TABLE} where extractor_data=:v", v=VID)[0]


# --- pure helpers ----------------------------------------------------------------

def test_check_video_files_prefers_original_with_known_extension():
    from alt2.services.archive import check_video_files
    item = ia_item([f("a.mp4", "derivative"), f("a.webm"), f("a.txt")])
    assert check_video_files(item) == "a.webm"
    assert check_video_files(ia_item([f("a.txt")])) is None


def test_get_image_file_prefers_video_id_name():
    from alt2.services.archive import get_image_file
    item = ia_item([f("other.jpg"), f(f"{VID}.webp"), f("__ia_thumb.jpg")])
    assert get_image_file(item) == f"{VID}.webp"


def test_get_image_file_skips_item_tiles_and_falls_back_to_ia_thumb():
    from alt2.services.archive import get_image_file
    tile = f("tile.jpg", fmt="Item Tile")
    assert get_image_file(ia_item([tile, f("x.png")])) == "x.png"
    assert get_image_file(ia_item([tile, f("__ia_thumb.jpg", "derivative")])) \
        == "__ia_thumb.jpg"
    assert get_image_file(ia_item([f("a.txt")])) is None


# --- get_ia_item -------------------------------------------------------------------

@pytest.mark.writes
def test_get_ia_item_stores_videofile_and_thumbnail(client, sql, fake_get_item):
    fake_get_item(ia_item([f(f"{VID}.mp4"), f(f"{VID}.jpg")]))
    url = run_get_ia_item(client)
    assert url == f"https://archive.org/download/youtube-{VID}/{VID}"
    videofile, thumb, novideo = row(sql)
    assert videofile == VID
    assert thumb == f"{VID}.jpg"
    assert not novideo


@pytest.mark.writes
def test_get_ia_item_without_video_marks_novideo(client, sql, fake_get_item):
    fake_get_item(ia_item([f(f"{VID}.jpg")]))
    assert run_get_ia_item(client).endswith("unavailable/unavailable")
    videofile, _thumb, novideo = row(sql)
    assert videofile is None
    assert novideo is True


@pytest.mark.writes
def test_get_ia_item_empty_metadata_changes_nothing(client, sql, fake_get_item):
    fake_get_item(ia_item(None))
    assert run_get_ia_item(client).endswith("unavailable/unavailable")
    assert row(sql)[0] is None and not row(sql)[2]


@pytest.mark.parametrize("exc", [requests.exceptions.ConnectionError("down"),
                                 requests.exceptions.RetryError("again")])
def test_get_ia_item_unreachable_is_unavailable(client, fake_get_item, exc):
    fake_get_item(exc=exc)
    assert run_get_ia_item(client).endswith("unavailable/unavailable")


def test_get_ia_item_for_a_video_we_do_not_have_is_unavailable(client, fake_get_item):
    # the file name is only stored (and the URL only returned) for a known row
    fake_get_item(ia_item([f("zz.mp4")], identifier="youtube-zz"))
    assert run_get_ia_item(client, "zz").endswith("unavailable/unavailable")
