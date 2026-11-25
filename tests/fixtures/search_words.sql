-- mv_search_words, as ytac creates it (altcensored/.claude/plans/search-words-view-ytac-handoff.md).
-- IF NOT EXISTS: a ytac whose views.create_all already makes it leaves this as a no-op.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_words AS
SELECT word, ndoc
FROM ts_stat($$SELECT to_tsvector('simple', COALESCE(title, '')) FROM public.mv_video$$)
WHERE length(word) BETWEEN 3 AND 30
  AND word !~ '^[0-9]+$';
CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_search_words_word ON mv_search_words (word);
CREATE INDEX IF NOT EXISTS ix_mv_search_words_trgm ON mv_search_words USING gin (word gin_trgm_ops);
