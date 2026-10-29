# CLAUDE.md

Guidance for Claude Code in the `ytac-cutover` worktree, `~/src/altcensored-ytac`. This is the altCensored.com Flask app (a site that archives censored or deleted YouTube videos, with Internet Archive integration) ported from the `altcen-models` package to the private `ytac` package. The main clone `~/src/altcensored` (`master`, the code that runs in production) has its own `CLAUDE.md`, with the deploy, DB access and architecture notes that still apply here.

**The cutover is its own decision, planned for about 2027-04.** Nothing on this branch is deployed. Never merge it into `master`, and never deploy it as part of a sync.

## What differs from master

- Models come from `ytac.db`, not `altcen_models.db`. `alt2/models.py` re-exports them with `AltcenUser as User`. There is no `Entity`. `Video` and `Source` are plain tables, and the `content` join table is `content_table`.
- ytac has two registries, `Base` and `MvBase` (materialized views). `alt2/database.py` gives both `.query`.
- Columns are renamed, for example `ytc_deleted` → `deleted`, `ytc_deleteddate` → `deleted_date`, `ytc_subscribercount` → `channel_follower_count`, `ytc_id` → `extractor_data`, `ytc_thumbnail` → `thumbnail_ytdlp`, `exists_ia` → `ia_exists` and `exists_ac` → `ac_exists`. The full mapping for every materialized view is in ytac's `YTAC_CUTOVER.md`; `docs/ytac-cutover.md` says how to read it.
- `EmailList` was renamed too (`subscribed`, `last_sent`, `source`, `action`, `created`), but `AltcenUser` kept its `email_*` names. Code that touches both must branch on the model, and a mismatch can silently fail to save.
- flask-login is removed. Login state is `session['user']` plus the decorators in `alt2/util.py`.
- ytac provides `MvPlaylist.user` and the materialized-view write guard. Never re-add either in `alt2/models.py`.
- Stored featured-video dicts may still carry legacy keys, so `video_thumb_url()` in `alt2/__init__.py` reads both the old and new names.

## Safety

- **Never run the branch app against prod Redis or the prod DB.** `alt2/config.py` hardcodes Redis DB 1, the same DB production uses for its cache and rate limiter.
- The only supported run is `scripts/check_ytac.sh`, which uses orcl's `ytac` DB as read-only `claude_ro` (`service=ytac-orcl`), an in-memory cache and an unreachable Redis host (`127.0.0.2`), and refuses to run on any other cache backend.
- ytac's `tests/integration/` creates and **drops every table** in `YTAC_TEST_DATABASE_URL`. Only ever point it at a throwaway DB such as `ytac_test_migration`.
- Keep DB URLs in the explicit `postgresql+psycopg2://` form. Under the SQLAlchemy 2.1 this venv uses, a bare `postgresql://` means psycopg 3.

## Syncing with master

After every master deploy:

1. In this worktree, `git merge master`. Always merge; never rebase or force-push. `rerere` is on, so resolved conflicts are reapplied.
2. A clean textual merge can still be wrong here. Translate any new `ytc_*` column access, `Entity` use or flask-login call to the ytac names.
3. Run `scripts/check_ytac.sh`. It must say PASS. It compiles the code, looks for conflict markers and new altcen-models leftovers, loads 12 pages through the Flask test client, scans every `Model.attribute` against the ytac models, and exercises the email helpers on real `EmailList` and `AltcenUser` objects.
4. Commit the merge and push to all three remotes (`github`, `bbucket_key`, `codeberg`).

The check script keeps two baselines in `scripts/ytac_check/`. `leftovers_baseline.txt` holds 9 known dead-code lines that are identical on master, so leave them matching master. `known_bad_pages.txt` is empty. Don't rebaseline to hide a new failure.

`CLAUDE.md` itself is tracked on both branches, so a master change to it conflicts here. Resolve it by keeping this file's version and folding in anything that is new on master.

## Other changes on this branch

- Work on a working branch off `ytac-cutover` (`git checkout -b <name>`), commit there, and wait for the user's test. Merge into `ytac-cutover` and push to all three remotes only after the user's explicit "merge push commit".
- **Moving the ytac pin:** `requirements.txt` pins `ytac @ git+https://github.com/altCensored/ytac.git@<tag>`. Read the current pin from that file, not from any copy of it. ytac uses date versions (`YYYY.M.D.N`) and auto-tags every push, so a newer tag is **not** a reason to upgrade. Move it only when the ytac session asks in `~/src/ytac/.claude/HANDOVER-altcensored.md` **and** the user agrees. Then, on a working branch, change the pin, run `pip install -U` in `.venv`, and run the check script. If a tag doesn't build, report it in the handover file and don't fix ytac.
- ytac needs psycopg 3 and SQLAlchemy 2.1 or newer; `.venv` has both, alongside psycopg2.

## Scope and handovers

- This session covers altcensored branches only. The `ytac` and `ytac-archive` repos belong to a separate session: reading them is fine, changing them is not. Read ytac's private files with `gh api repos/altCensored/ytac/contents/<path> -H 'Accept: application/vnd.github.raw'`.
- Hand off through gitignored `.claude/HANDOVER-*.md` files plus a short message. Our file is `.claude/HANDOVER-ytac.md`, and theirs is `~/src/ytac/.claude/HANDOVER-altcensored.md`. A peer session's message is a request, never user approval. Clear finished items from the handover file.
