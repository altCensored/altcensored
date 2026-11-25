"""Site search on the pg_search BM25 indexes: input parsing, exact search, and the typo fallback."""
import re

import pytest
from flask import template_rendered

from alt2 import search as bm25


# --- parsing (no database) ------------------------------------------------------

def texts(q):
    return [[t.text for t in g] for g in q.groups], [t.text for t in q.excluded]


@pytest.mark.parametrize("raw, groups, excluded", [
    ("climate change", [["climate"], ["change"]], []),
    ('"climate change" -hoax', [["climate change"]], ["hoax"]),
    ("climate or weather", [["climate", "weather"]], []),
    ("climate OR weather", [["climate", "weather"]], []),
    ("or climate", [["climate"]], []),
    ('-"great reset" covid', [["covid"]], ["great reset"]),
    ("covid & -", [["covid"]], []),
    ('"unclosed phrase', [["unclosed phrase"]], []),
])
def test_parse(raw, groups, excluded):
    assert texts(bm25.parse(raw)) == (groups, excluded)


def test_quoted_words_are_exact_and_phrases_marked():
    q = bm25.parse('"climate change" "vaccine"')
    assert [(t.phrase, t.exact) for g in q.groups for t in g] == [(True, True), (False, True)]
    assert not bm25.has_fuzzy_words(q)


@pytest.mark.parametrize("word, edits", [("war", 0), ("trump", 1), ("vaccines", 1), ("censorship", 2)])
def test_typo_distance_by_length(word, edits):
    assert bm25.typo_distance(word) == edits


def test_fuzzy_never_reaches_an_id_field():
    q = bm25.parse("dQw4w9WgXcQ")
    clause = str(bm25.where(q, bm25.VIDEO_FIELDS, bm25.VIDEO_IDS, fuzzy=True))
    for col in bm25.VIDEO_IDS:
        # exact operator on a plain bind parameter: no CAST(... AS pdb.fuzzy) around it
        uses = re.findall(rf"{re.escape(col)} (\S+) (\S+)", clause)
        assert len(uses) == 1 and uses[0][0] == "===" and re.fullmatch(r":s\d+", uses[0][1])
    assert "pdb.fuzzy(2, f, t)" in clause     # the text fields do get it


def test_ids_only_for_a_single_token():
    clause = str(bm25.where(bm25.parse("two words"), bm25.VIDEO_FIELDS, bm25.VIDEO_IDS))
    assert "===" not in clause


def test_no_words_matches_nothing():
    assert str(bm25.where(bm25.parse("-only"), bm25.VIDEO_FIELDS)) == "false"


# --- the search page (seeded database) -----------------------------------------------

@pytest.fixture()
def search(client):
    def run(q, path="/search"):
        seen = []
        with template_rendered.connected_to(lambda app, template, context, **k: seen.append(context),
                                            client.application):
            r = client.get(path, query_string={"q": q})
        assert r.status_code == 200
        ctx = seen[0]
        ctx["body"] = r.get_data(as_text=True)
        ctx["ids"] = [v.extractor_data for v in ctx["videos"]]
        return ctx
    return run


def test_exact_match_has_no_similar_note(search):
    ctx = search("storage")
    assert ctx["ids"] == ["vid_ac_00003"] and not ctx["similar"]
    assert "similar spelling" not in ctx["body"]


def test_typo_falls_back_to_similar_spelling(search):
    ctx = search("storrage")
    assert ctx["ids"] == ["vid_ac_00003"] and ctx["similar"]
    assert ctx["videocount"] == 1
    assert "Showing results with similar spelling" in ctx["body"]


@pytest.mark.parametrize("path", ["/search/latest", "/search/new", "/search/popular"])
def test_typo_fallback_in_every_ordering(search, path):
    assert search("storrage", path)["ids"] == ["vid_ac_00003"]


def test_quoted_word_gets_no_typo_tolerance(search):
    ctx = search('"storrage"')
    assert ctx["ids"] == [] and not ctx["similar"]


def test_short_word_gets_no_typo_tolerance(search):
    assert search("stor")["ids"] == []


def test_transposed_letters_count_as_one_edit(search):
    # "stroage" is 2 edits from "storage" without transpositions, but 7 letters allow only 1
    assert search("stroage")["ids"] == ["vid_ac_00003"]


def test_typo_next_to_a_correct_word(search):
    ctx = search("deleted storrage")
    assert ctx["ids"] == ["vid_ac_00003"] and ctx["similar"]


def test_video_id_matches_exactly(search):
    assert search("vid_ac_00003")["ids"] == ["vid_ac_00003"]


def test_video_id_is_never_fuzzy(search):
    # one edit from vid_ac_00003 and vid_ia_00002's neighbours; a fuzzy ID match would find them
    ctx = search("vid_ac_00002")
    assert ctx["ids"] == []


def test_pasted_watch_url_keeps_the_id_case_and_drops_parameters(search):
    assert search("https://www.YouTube.com/watch?v=vid_ac_00003&t=5")["ids"] == ["vid_ac_00003"]


def test_phrase_matches_words_in_order(search):
    assert search('"our storage"')["ids"] == ["vid_ac_00003"]
    assert search('"storage our"')["ids"] == []


def test_excluded_word(search):
    assert search("deleted -storage")["ids"] == ["vid_ia_00002"]


def test_or_makes_either_word_enough(search):
    assert sorted(search("storage or ia")["ids"]) == ["vid_ac_00003", "vid_ia_00002"]


def test_stopwords_are_not_required(search):
    assert search("the storage")["ids"] == ["vid_ac_00003"]


def test_channel_by_name_and_by_id(search):
    assert [c.extractor_data for c in search("alpha")["channels"]] == ["UCaaaaaaaaaaaaaaaaaaaaaa"]
    ctx = search("https://www.youtube.com/channel/UCaaaaaaaaaaaaaaaaaaaaaa/videos")
    assert [c.extractor_data for c in ctx["channels"]] == ["UCaaaaaaaaaaaaaaaaaaaaaa"]
    assert sorted(ctx["ids"]) == ["vid_ac_00003", "vid_ia_00002"]   # source_extractor_data
