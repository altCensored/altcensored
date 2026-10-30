"""Which source _resolve_video_url picks for a video. S3 and archive.org are stubbed."""
from types import SimpleNamespace

import pytest

SERVER = "https://videos.test/"
IAURL = "https://archive.org/download/youtube-"
UNAVAILABLE = SERVER + "unavailable/unavailable"


def video(**kw):
    base = dict(exists_ac=None, exists_ia=None, dark_ia=None, restricted_ia=None,
                loggedin_ia=None, novideo_ia=None, videofile=None, thumbnail=None,
                extractor_data="abc")
    return SimpleNamespace(**{**base, **kw})


@pytest.fixture()
def resolve(app, monkeypatch):
    import alt2.video

    def run(v, s3=False, ia="IA-LOOKUP"):
        def s3_check(_):
            if isinstance(s3, Exception):
                raise s3
            return s3
        monkeypatch.setattr(alt2.video, "check_ac_object_exists", s3_check)
        monkeypatch.setattr(alt2.video, "get_ia_item", lambda _: ia)
        with app.app_context():
            return alt2.video._resolve_video_url(v, "abc")
    return run


def test_own_storage_when_object_exists(resolve):
    assert resolve(video(exists_ac=True), s3=True) == SERVER + "abc/abc"


def test_exists_ac_but_object_missing_falls_through(resolve):
    assert resolve(video(exists_ac=True, exists_ia=False), s3=False) == UNAVAILABLE


def test_s3_error_is_treated_as_missing(resolve):
    assert resolve(video(exists_ac=True, exists_ia=False), s3=OSError()) == UNAVAILABLE


@pytest.mark.parametrize("flag", ["dark_ia", "restricted_ia", "loggedin_ia", "novideo_ia"])
def test_ia_restrictions_are_unavailable(resolve, flag):
    assert resolve(video(**{flag: True, "exists_ia": True})) == UNAVAILABLE


def test_videofile_builds_ia_download_url(resolve):
    assert resolve(video(videofile="clip.mp4", exists_ia=True)) == IAURL + "abc/clip"


def test_exists_ia_false_is_unavailable(resolve):
    assert resolve(video(exists_ia=False)) == UNAVAILABLE


@pytest.mark.parametrize("exists_ia", [None, True])
def test_unknown_or_true_asks_internet_archive(resolve, exists_ia):
    # None means "unknown", so only an explicit False skips the lookup
    assert resolve(video(exists_ia=exists_ia)) == "IA-LOOKUP"
