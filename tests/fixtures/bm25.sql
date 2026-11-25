-- pg_search BM25 indexes, as ytac creates them (ytac-suite/.claude/plans/pg-search-bm25-results-for-altcensored.md).
-- IF NOT EXISTS: a ytac whose views.create_all already makes them leaves these as no-ops.
CREATE INDEX IF NOT EXISTS ix_mv_video_bm25 ON mv_video USING paradedb (
    id,
    (title::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (description::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (source_title::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (category::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    ((tags::text)::pdb.unicode_words('alias=tags', 'ascii_folding=true', 'stemmer=english')),
    (extractor_data::pdb.literal),
    (source_extractor_data::pdb.literal),
    published,
    view_count
);
CREATE INDEX IF NOT EXISTS ix_mv_channel_bm25 ON mv_channel USING paradedb (
    id,
    (title::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (description::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (uploader_id::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (extractor_data::pdb.literal)
);
CREATE INDEX IF NOT EXISTS ix_mv_playlist_bm25 ON mv_playlist USING paradedb (
    id,
    (title::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (description::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (hashid::pdb.literal),
    public
);
CREATE INDEX IF NOT EXISTS ix_mv_altcen_user_bm25 ON mv_altcen_user USING paradedb (
    id,
    (username::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    (description::pdb.unicode_words('ascii_folding=true', 'stemmer=english')),
    public
);
