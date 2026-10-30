"""The parity script's comparison logic, on in-memory rows (no database)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import parity_player as pp  # noqa: E402


def row(**kw):
    base = dict(ac=None, ia=True, dark=None, restricted=None, loggedin=None,
                novideo=None, videofile=None, thumbnail=None)
    return {**base, **kw}


def test_identical_rows_have_no_diff():
    assert pp.classify(row(), row()) == []


def test_none_and_false_flags_are_equal():
    assert pp.classify(row(dark=None, ac=None), row(dark=False, ac=False)) == []


def test_null_ia_to_false_is_the_known_difference():
    assert pp.classify(row(ia=None), row(ia=False)) == ["ia-null->false"]


def test_real_ia_change_is_flagged():
    assert pp.classify(row(ia=True), row(ia=False)) == ["ia"]
    assert pp.classify(row(ia=None), row(ia=True)) == ["ia"]


def test_other_fields_are_flagged():
    assert pp.classify(row(videofile="a.mp4"), row(videofile=None)) == ["videofile"]
    assert pp.classify(row(novideo=True), row(novideo=False)) == ["novideo"]


def test_compare_finds_one_sided_rows():
    old = {"a": row(), "b": row(), "c": row(ia=None)}
    new = {"a": row(), "c": row(ia=False), "d": row()}
    only_old, only_new, by_diff = pp.compare(old, new)
    assert only_old == ["b"] and only_new == ["d"]
    assert by_diff == {("ia-null->false",): ["c"]}
