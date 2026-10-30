"""The views parity script's comparison logic, on in-memory rows (no database)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import parity_views as pv  # noqa: E402


def blank(view):
    return {name: None for name in pv.SPEC[view][1]}


def row(view, **kw):
    return {**blank(view), **kw}


def test_every_spec_has_a_key_and_a_pair_of_columns_per_field():
    for view, (key, fields) in pv.SPEC.items():
        assert len(key) == 2
        assert fields and all(len(spec) == 3 for spec in fields.values())


def test_identical_rows_do_not_differ():
    r = row("mv_channel", title="A", deleted=False)
    assert pv.classify("mv_channel", r, dict(r)) == ([], [])


def test_none_and_empty_string_are_equal():
    assert pv.classify("mv_channel", row("mv_channel", title=""),
                       row("mv_channel", title=None)) == ([], [])


def test_arrays_compare_by_content_not_type():
    a = row("mv_playlist", videos=["x", "y"])
    b = row("mv_playlist", videos=("x", "y"))
    assert pv.classify("mv_playlist", a, b) == ([], [])
    c = row("mv_playlist", videos=["y", "x"])
    assert pv.classify("mv_playlist", a, c) == (["videos"], [])


def test_a_changed_fixed_field_is_unexpected():
    unexpected, drift = pv.classify("mv_channel", row("mv_channel", archive=True),
                                    row("mv_channel", archive=False))
    assert unexpected == ["archive"] and drift == []


def test_a_changed_counter_is_only_drift():
    unexpected, drift = pv.classify("mv_channel", row("mv_channel", views=10),
                                    row("mv_channel", views=99))
    assert unexpected == [] and drift == ["views"]


def test_compare_reports_one_sided_keys_and_groups_by_field():
    old = {"a": row("mv_category", id=1), "b": row("mv_category", id=2),
           "c": row("mv_category", id=3)}
    new = {"a": row("mv_category", id=1), "b": row("mv_category", id=9),
           "d": row("mv_category", id=4)}
    only_old, only_new, unexpected, drift = pv.compare("mv_category", old, new)
    assert only_old == ["c"] and only_new == ["d"]
    assert unexpected == {"id": ["b"]} and drift == {}


@pytest.mark.parametrize("view", sorted(pv.SPEC))
def test_report_counts_problems(view, capsys):
    old = {"k": row(view)}
    assert pv.report(view, old, {"k": row(view)}, 3) == 0
    assert pv.report(view, old, {}, 3) == 1
    assert "only in old: 1" in capsys.readouterr().out
