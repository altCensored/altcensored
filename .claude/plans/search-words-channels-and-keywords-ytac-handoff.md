# Hand-off to the ytac Claude: channel names in mv_search_words, and find_text keyword fixes

From: the altcensored Claude, 2026-11-25. Approved by the user. Follows `search-words-view-ytac-handoff.md`.
No altcensored code change is needed for either item.

## 1. Count channel names in the spelling vocabulary

Change the `ts_stat` input of `mv_search_words` from the title alone to title plus the video's channel name
(`source_title`, already in `mv_video`). A channel's name then counts once per video, so it is a realistic
correction target:

```sql
CREATE MATERIALIZED VIEW mv_search_words AS
SELECT word, ndoc
FROM ts_stat($$SELECT to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(source_title, ''))
              FROM public.mv_video$$)
WHERE length(word) BETWEEN 3 AND 30
  AND word !~ '^[0-9]+$';
```

Same columns, same two indexes, keep `public.mv_video` schema-qualified. `ndoc` now means "videos whose title or
channel name contains the word".

Measured on production (read-only, temp table, 2026-11-25):

| | live view (titles) | proposed (titles + channel names) |
|---|---|---|
| words | 257,126 | 262,286 (+5,160) |
| build | 4.4 s | 7.2 s |
| size with indexes | | 30 MB |

- All earlier checks unchanged: holocost, isreal, censorhsip, vacine, stroage, obmaa, jewsih, gardacil are
  corrected right; plandemic, navalny, tartaria, gates, trump, mrna, qanon, fauci, assange, zelensky are not
  touched.
- Misspelt channel names are now corrected: mesrey -> mersey, sptonik -> spotnik, arunlba -> arnulba,
  booirix -> boiorix, masrchliederkanal -> marschliederkanal.

**Deploy:** rebuild only `mv_search_words`; no other view and no altcensored change. With the user's go. And,
learned today: if this ships in a new ytac release, the app's installed ytac doesn't need it (altcensored
reads `mv_search_words` with plain SQL, not through a ytac model), but **any change to a view altcensored maps
through `ytac.db` needs the app's ytac upgraded in the same step** (`/opt/altcen/altcensored/venv`), or the site
500s, as it did 16:57-17:02 UTC today when `document` was dropped.

## 2. find_text: one misspelling, and stems that only work with substring matching

Not adding `find_text` to the vocabulary (94% of its words are already there). But checking it found:

- **`gardacil` is misspelt**: the word in titles is `gardasil` (75 titles; `gardacil` 0). As a saved keyword it
  misses every Gardasil video in `ytac-archive video find --saved-terms`.
- **Cut-off stems** that rely on `ILIKE '%term%'` substring matching: `Antizionis`, `christian zionis`,
  `extreme zionis`, `chemically castrat`, `child mutil`, `holocaust denia`, `jewish supremac`, `pedophil`.
  They work today, but would match nothing if keyword search ever moves to word matching (BM25 or tsvector).
  Several also duplicate full terms that exist (`Holocaust denial`, `genital mutilation`).

The keyword list is the user's: report these to the user rather than editing `find_text`.

## 3. Also outstanding from today (FYI)

- Push git tags for the 2026.11.25.x releases: the app's venv had to be installed from the local checkout
  (`cfc9d37`) because no `v2026.11.25.*` tag exists on GitHub.
- `mv_video_old` (1,550 MB), `mv_video_fix` (1,549 MB) and `mv_channel_old` (39 MB) are still on production.
