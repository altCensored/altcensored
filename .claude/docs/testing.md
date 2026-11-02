# Testing

How the test suites work and what they guard. Commands, the per-file table and the
blueprint coverage matrix are in `tests/README.md`; this document explains the design
and the gaps. Production rules and safety are in `CLAUDE.md`.

## Four layers

| Layer | Where | Needs | Checks |
|---|---|---|---|
| Pytest suite | `tests/` (21 `test_*.py`, ~330 test functions, 51 `parametrize`) | scratch PostgreSQL DB on www2 | app behaviour through the Flask test client |
| Parity scripts | `scripts/parity_player.py`, `scripts/parity_views.py` | two libpq services, read-only | legacy vs ytac data, row by row |
| Smoke check | `scripts/check_ytac.sh` | read-only ytac service (`YTAC_CHECK_SERVICE`) | compile, conflict markers, new legacy leftovers, every page renders, model attributes exist, email helpers |
| Mutation check | `scripts/mutation_check.py` | www2 over ssh | that the suite fails when the code is broken (17 mutations) |

There is no CI (`.github/` and pre-commit config are absent). Tests run by hand through
`tests/run_www2.sh`.

## Pytest harness

- **Real app, real PostgreSQL, no mocks of the database.** `conftest.py` builds the app
  with `create_app({TESTING, no CSRF, no rate limit})`. The cache is a `NullCache` and the
  limiter is in memory, so Redis is never touched.
- **Database guard.** `ALTC_TEST_DATABASE_URL` is required and the DB name must end in
  `_test`, or `pytest_configure` raises `UsageError`. The suite drops and recreates every
  table, so the guard is the only thing between a typo and data loss. Use
  `altc-www2-test-rw` on www2; never www, orcl or the `ytac`/`altcen` rehearsal copies.
- **Env is set before `alt2` is imported** (`config.py` reads it at import time), which is
  why the setup lives in `pytest_configure` and the app import is inside fixtures.
- **Session-scoped `engine` seeds once** (`seed.setup`: wipe, create tables and views,
  load, refresh). `app` is also session-scoped; `client` is per test and sends
  `X-Forwarded-Proto: https` and `Host: altcensored.com` to avoid the https redirect.
- **Seed is a neutral spec with two loaders** (`seed.py`): 2 channels, 4 videos
  (live, on IA, on own storage, nowhere), 3 users (`admin`, `alice`, `newbie`), 1
  playlist, 2 categories. Tests rely on these exact values. `vid_gone_0004` must stay out
  of `mv_video`, which verifies the view definition and not only the data.
- **Materialized views are real.** Legacy loads prod's DDL from `fixtures/matviews.sql`;
  ytac uses `ytac.views`. Base rows are inserted, then views refreshed, as the scraper does.
- **Two schemas, one test body.** `schema.py` maps column names that differ
  (`CHANNEL_WHERE`, `VIDEO_TABLE`, `AC_VIEWS`, `ADD_VERB`, ...). Tests import from it
  instead of branching. `@pytest.mark.legacy` / `ytac` skip the other backend in
  `pytest_collection_modifyitems`.
- **Writes are undone by re-seeding.** Tests marked `writes` (66 of them) trigger a full
  `seed.setup` afterwards (~1 s each) rather than transaction rollback, because the app
  commits through its own session. Unmarked tests must not write.

### Autouse isolation fixtures

| Fixture | Effect |
|---|---|
| `no_network` | `check_ac_object_exists` and `get_ia_item` raise; stub them again to get an answer |
| `outbox` | `send_email` appends `(args, kwargs)` to a list |
| `shell` | `local_command` and `ssh_command` in `alt2.admin` and `alt2.util` are recorded, never run |
| `_reseed_after_writes` | re-seeds after `writes` tests |

Helpers: `login(client, name)` posts the real form (GET first, because login needs
`session['navtabs']`); `user_client` / `admin_client`; `sql(query, **params)` returns row
tuples; `flashes(client)` reads queued flashes (only after a redirect).

## What each group of tests is for

- **Behaviour by blueprint:** `test_auth`, `test_playlist`, `test_user`, `test_settings`,
  `test_admin`, `test_video_api`, `test_player`, `test_archive`, `test_listings`,
  `test_pages`, `test_sitemap_feeds`, `test_pagination`. Happy path asserts content or DB
  state, not only the status code; gates and failures are asserted too.
- **Cross-cutting:** `test_app` (locale, error pages, headers, cookie hook, template
  filters; the largest file), `test_csp` (parses each page's HTML and checks every loaded
  origin against the CSP the same response sends, since the test client does not enforce
  it), `test_i18n` (catalogs vs source strings and `.po` vs `.mo`), `test_util`.
- **Infrastructure behaviour:** `test_cache_limits` builds a second app with `SimpleCache`
  and the limiter on, then restores the module-global cache config and turns the limiter off.
- **Cutover:** `test_cutover_divergences` pins legacy-vs-ytac differences on purpose (e.g.
  NULL `exists_ia`); `test_parity_*` test the comparison logic of the scripts on in-memory
  rows with no database.
- **Harness self-test:** `test_harness` checks seed counts and that `/` renders.

## Known failures (strict xfail)

An xfail that starts passing fails as XPASS, the cue to delete the marker.

- `test_app.py`: `iso8601duration(0)` returns `'PT'`, and `hourminsec(5)` returns `':05'`
  (`lstrip("0")` eats the minute digit).
- `test_i18n.py`: 31 strings used in code are in no catalog (per locale: de, es, fr, it,
  nl, pt, sv).
- `test_user.py`: account delete with playlists.

## Parity and smoke scripts

- `parity_player.py OLD NEW [--new-table video]` compares the 8 fields `_resolve_video_url`
  reads across `mv_video`. Exit 0 only if every difference is the known NULL `exists_ia`
  to False.
- `parity_views.py OLD NEW [--view ...]` covers `mv_channel`, `mv_category`,
  `mv_playlist` and the user view. Differences are `UNEXPECTED`, `drift` (counters;
  never fail) or one-sided keys. Both open read-only libpq services.
- `check_ytac.sh [--rebaseline]` greps `alt2/` for legacy leftovers against
  `scripts/ytac_check/leftovers_baseline.txt`, then renders pages through the test client
  against a real read-only DB, skipping `known_bad_pages.txt`. Prints PASS/FAIL.

## Mutation check

`mutation_check.py` copies the tree to `~/mut/m<N>` on www2, applies one exact-text
replacement, runs the suite with `-x` on the legacy stack and deletes the copy. Results:
`CAUGHT`, `MISSED` (a missing test), `SKIPPED` (the text no longer occurs once; update
`MUTATIONS`), `UNKNOWN`. It uses the same www2 test DB as `run_www2.sh`, so never run
both at once. Add a mutation when you add a guard worth protecting.

## Strengths

- Tests hit the real SQL and the real materialized views, so schema drift fails here.
- Side effects (network, mail, shell) are blocked for every test by default.
- The mutation check measures whether the tests can fail, not only whether they pass.
- Both schemas are covered by one suite during the cutover.

## Gaps and risks

- **No CI or pre-commit.** Nothing runs the suite on push; `run_www2.sh` needs the branch
  pushed first (or `--local` for tests only; `alt2/` changes cannot be tested that way).
- **Single shared test DB.** `run_www2.sh`, the mutation check and any other session on
  `altcen_test` collide. Runs must be serial.
- **Re-seed per write test** costs about a second each (~66 s of seeding per run).
- **Only the legacy stack is mutated;** ytac is checked by running the suite on it.
- **Not covered:** OAuth `authorize`/`callback`, `mass_email` / bounce / email-list
  uploads, the real Turnstile check, real S3 and archive.org, browser behaviour. The
  manual checklist is in `tests/README.md`.
- **Seed is tiny** (4 videos), so pagination tests set the page size to 1, and there is no
  load or large-data testing.
- **Flash quirk:** `flashes()` only sees redirect flashes; a directly rendered view shows
  them in the body.

## Never do

- Point `ALTC_TEST_DATABASE_URL` at www or orcl, or at the `ytac` / `altcen` DBs on www2.
- Run the ytac or ytac-archive `tests/integration/` suites against a real DB; use the
  empty `ytac_test_migration` on www2 (`ytac-test-www2-rw`).
- Run tests on a prod node.
