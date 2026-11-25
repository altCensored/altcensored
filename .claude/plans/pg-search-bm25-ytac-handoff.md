# Hand-off to the ytac Claude: pg_search BM25 indexes on the altcensored matviews

From: the altcensored Claude, 2026-11-25. Decision by the user: altcensored search moves to
ParadeDB pg_search (BM25) with typo tolerance as a **fallback** (exact search first; fuzzy only
when the exact search finds little or nothing). This document is what ytac needs to provide.

## Scope

- ytac owns the matviews and their indexes (`ytac/ytac/views.py`). Add BM25 indexes there.
- altcensored owns the queries (`alt2/video.py`) and its test fixture. Don't touch altcensored.
- **Additive only.** Keep every existing column and index, including the `document` tsvector
  columns and their GIN indexes. altcensored keeps using them until it switches over; removing
  them is a later, separate change.

## Infrastructure (needs the user's explicit go at each step)

1. Install pg_search for PG 18 on www (Debian 13 trixie `.deb` from the ParadeDB GitHub releases;
   v0.27.1 at the time of writing). pgvector is a prerequisite.
2. `shared_preload_libraries = 'pg_search'`, then **restart Postgres on www**. That restarts
   production `ytac` too, so schedule it with the user.
3. `CREATE EXTENSION pg_search CASCADE;` needs a superuser. Do it **first in `ytac_ac_test` only**.
4. Install the same version on **orcl** before any `ytac` dump containing a BM25 index is
   restored there, or the restore fails on the `CREATE INDEX`.

## Indexes wanted

Syntax below is a sketch. **Check it against the docs of the installed version**: the access
method name (`bm25` vs `paradedb`), `key_field`, and the tokenizer cast syntax changed between
releases.

Tokenizer for free-text fields: Unicode words, lowercase, **ASCII folding on** (cancion finds
canción), **English stemming on** (same as the current `english` config, so exact search doesn't
get worse for anyone). Identifier fields use the **literal** (exact, untokenized) tokenizer.

### mv_video (the one that matters, ~486K rows)

| Column | Role | Tokenizer |
|---|---|---|
| `id` | key field, sort (`latest`, tiebreaker) | – |
| `title` | text search | words + fold + stem |
| `description` | text search | words + fold + stem |
| `source_title` | text search (channel name) | words + fold + stem |
| `category` | text search | words + fold + stem |
| tags | text search | words + fold + stem |
| `extractor_data` | exact ID match (pasted video URL or ID) | literal |
| `source_extractor_data` | exact ID match (channel ID) | literal |
| `published` | sort (`newest`) | fast field |
| `view_count` | sort (`popular`) | fast field |

`tags` is jsonb. If pg_search can't index the jsonb array as text cleanly, add a plain text column
to the matview, e.g. `array_to_string(ARRAY(SELECT jsonb_array_elements_text(v.tags)), ' ') AS tags_text`,
and index that.

### mv_channel (~18K)
`id` (key, tiebreaker), `title`, `description`, `uploader_id` (words + fold + stem),
`extractor_data` (literal).

### mv_playlist (~550)
`id` (key, tiebreaker), `title`, `description` (words + fold + stem), `hashid` (literal),
`public` (filter).

### mv_altcen_user (~9K)
`id` (key, tiebreaker), `username`, `description` (words + fold + stem), `public` (filter).

## Acceptance checks (run in `ytac_ac_test`, report the results back)

1. `views.create_all` builds all views plus the BM25 indexes. Then `views.refresh_all`
   (`REFRESH MATERIALIZED VIEW CONCURRENTLY`) succeeds **with** the BM25 indexes present. This is
   undocumented by ParadeDB and is the go/no-go item. Report the refresh time for `mv_video`
   with and without the BM25 index.
2. Exact: a stemmed match works, e.g. `title ||| 'vaccines'` finds titles containing "vaccine".
3. Fuzzy: `title ||| 'vacine'::pdb.fuzzy(1)` finds "vaccine". Also check whether fuzzy terms are
   stemmed: does `'vacines'::pdb.fuzzy(1)` find "vaccines"?
4. ASCII folding: `'cancion'` finds "canción".
5. ID: `extractor_data` exact match on a real 11-character video ID returns exactly that video, and
   `fuzzy` is not applied to that field.
6. Top-K: `... ORDER BY published DESC, id DESC LIMIT 20` and the `view_count` and `pdb.score(id)`
   variants show `TopKScanExecState` in `EXPLAIN`.
7. Count: time `SELECT count(*) FROM mv_video WHERE title ||| 'trump'` (a common term).
8. Report: the exact `CREATE INDEX` statements that worked, index sizes, and the pg_search version.

## Hand-back

When the checks pass, tell the altcensored Claude (via the user) the index and field names and the
working query syntax. altcensored then writes the exact-then-fuzzy fallback in `alt2/video.py`
against `ytac_ac_test`.
