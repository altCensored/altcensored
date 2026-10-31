# Tests

Real app, real PostgreSQL, small seeded dataset (`seed.py`). Needs a dedicated
database whose name ends in `_test`; the suite drops and recreates everything in it.

    ALTC_TEST_DATABASE_URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw' \
      venv/bin/python -m pytest tests

On www2 the service entry avoids handling a password. Never point this at www or orcl.
`pip install -r requirements-test.txt` adds pytest.

`tests/run_both.sh [pytest args]` rsyncs `tests/` to www2 and runs them in both
checkouts: `/opt/altcen/altcensored-master` (legacy schema) and
`/opt/altcen/altcensored` (`ytac-cutover`). One run covers one schema, chosen by
which package the venv has. A failure on one stack only is a cutover regression.

## Layout

| File | Covers |
|---|---|
| `seed.py`, `schema.py` | the neutral dataset, loaders for both schemas, per-backend column names |
| `test_auth.py` | login/logout, decorators, reset and confirm mail |
| `test_playlist.py`, `test_user.py` | playlists, watch later, history, profiles, account delete |
| `test_settings.py` | site and user settings |
| `test_admin.py` | admin gate, channel/video updates, recorded shell dispatch |
| `test_video_api.py`, `test_player.py`, `test_archive.py` | player endpoints, view counter, source choice, archive.org |
| `test_sitemap_feeds.py`, `test_listings.py`, `test_pages.py` | sitemaps, feeds, listings, pagination |
| `test_app.py` | locale, error pages, headers, loggedin cookie hook, template filters |
| `test_cache_limits.py` | real cache and rate limiter (a second app, see its docstring) |
| `test_i18n.py` | translation catalogs vs. the strings in the code |
| `test_cutover_divergences.py` | legacy-vs-ytac differences pinned on purpose (NULL `exists_ia`, feed thumbnail) |
| `test_parity_player.py`, `test_parity_views.py` | the comparison logic of `scripts/parity_player.py` and `scripts/parity_views.py` |

## Conventions

- `@pytest.mark.writes`: the test changes the database, which is re-seeded afterwards
  (about a second). The thread stub in `test_video_api.py` adds the marker itself.
- `@pytest.mark.legacy` / `ytac`: only meaningful on that schema, skipped on the other.
- `xfail(strict=True)` marks a known bug and says which. When it is fixed the test
  fails as XPASS, which is the cue to delete the marker.
- Network and shell are blocked by autouse fixtures: S3 and archive.org raise, mail
  goes to the `outbox` list, admin `local_command`/`ssh_command` are recorded in
  `shell`. Stub again in a test that needs a real answer.
- Log in with `login(client, name)` (the real form), or the `user_client` /
  `admin_client` fixtures. Seeded users: `admin`, `alice` (public, owns a playlist),
  `newbie` (unverified), all with `seed.PASSWORD`.
- `flashes(client)` only sees messages left in the session by a redirect; a view that
  renders directly shows its flashes in the response body.

`fixtures/` holds UI text and the materialized-view DDL exported from prod; re-export
`matviews.sql` when a migration changes a view. The legacy seed also converts the
account tables' timestamps to `timestamptz`, as in prod, because `altcen_models`
declares them naive.

## Not covered

`mass_email`, `update_bounce` and `add_email_list` uploads (write files, send mail),
OAuth, Turnstile registration, real S3/archive.org, and browser behaviour. Check those by
hand after a change.
