# Hand-off to the ytac Claude: a word-frequency view for spelling correction

From: the altcensored Claude, 2026-11-25. Decided by the user (option A): altcensored corrects misspelt
search words ("holocost" -> "holocaust") from the site's own vocabulary. ytac owns the view; altcensored
builds the correction in parallel against the definition below. **Deploy order: this view in production
before the altcensored change, or every search that tries a correction fails.**

## The view

```sql
CREATE MATERIALIZED VIEW mv_search_words AS
SELECT word, ndoc
FROM ts_stat($$SELECT to_tsvector('simple', COALESCE(title, '')) FROM public.mv_video$$)
WHERE length(word) BETWEEN 3 AND 30
  AND word !~ '^[0-9]+$';

CREATE UNIQUE INDEX ix_mv_search_words_word ON mv_search_words (word);
CREATE INDEX ix_mv_search_words_trgm ON mv_search_words USING gin (word gin_trgm_ops);
```

- `word`: lowercase, unstemmed ('simple' config). `ndoc`: number of `mv_video` titles containing it.
- **Keep `public.mv_video` schema-qualified inside the `ts_stat` string.** Since PG 17, CREATE and REFRESH
  MATERIALIZED VIEW run with `search_path = pg_catalog, pg_temp`, and the string is only resolved at run
  time: unqualified, it fails with `relation "mv_video" does not exist` (found in altcensored's tests;
  corrected here 2026-11-25).
- It reads `mv_video`, so it must be created and refreshed **after** `mv_video` (last in `_VIEWS`).
- The unique index is required for `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
- Needs `pg_trgm`, already installed in production `ytac` and available in `ytac_ac_test`.
- The app role `ytac` must be able to SELECT it, as with the other views.

## Measured on production (read-only, temp table as `claude_ro`)

- 257,111 words, 12 MB, built in 4.4 s. The nightly refresh grows by a few seconds.
- Lookups (trigram candidates, then edit distance in Python) take 2-28 ms per word. Of 18 test typos, all
  18 are corrected right (holocost, isreal, censorhsip, stroage, obmaa, ...). Of 12 rare but correct words
  (plandemic, navalny, tartaria, mrna, ...), none is changed.

## Asked of ytac

1. Add `mv_search_words` and its two indexes to `views.py` (create and refresh, after `mv_video`).
2. Create it in production with the user's go (a small build, about 5 s; no rebuild of the other views).
3. Tell the user when it is live in production; altcensored then deploys.

## altcensored side (FYI)

Tests create the view from `tests/fixtures/search_words.sql` with `IF NOT EXISTS`, so ytac's `create_all`
making it first is harmless, as with `bm25.sql`.

## Also for the user/ytac

`claude_rw` can no longer log in to `ytac_bm25_test` ("password authentication failed"); the password or
the `~/.pgpass` entry changed. altcensored doesn't need that database any more.
