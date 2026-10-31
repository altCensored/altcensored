# Tests

Real app, real PostgreSQL, small seeded dataset (`seed.py`). Needs a dedicated
database whose name ends in `_test`; the suite drops and recreates everything in it.

    ALTC_TEST_DATABASE_URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw' \
      venv/bin/python -m pytest tests

On www2 the service entry avoids handling a password. Never point this at www or orcl.
`pip install -r requirements-test.txt` adds pytest.

`tests/run_both.sh [--local] [pytest args]` runs the suite in both www2 checkouts:
`/opt/altcen/altcensored-master` (`master`, legacy schema) and `/opt/altcen/altcensored`
(`ytac-cutover`). Both are git clones, so by default it does `git pull --ff-only` in each
and prints the commit it tested. That means the code must be pushed first. To test
uncommitted work, use `--local`: it rsyncs this clone's `tests/`, `pytest.ini` and
`scripts/parity_*.py` over the checkouts and restores them afterwards. The script
refuses to run if a www2 checkout has uncommitted changes. One run covers one schema,
chosen by which package the venv has. A failure on one stack only is a cutover
regression.

## Layout

| File | Covers |
|---|---|
| `seed.py`, `schema.py` | the neutral dataset, loaders for both schemas, per-backend column names |
| `test_auth.py` | login/logout, decorators, reset and confirm mail |
| `test_playlist.py`, `test_user.py` | playlists, watch later, history, profiles, account delete |
| `test_settings.py` | site and user settings |
| `test_admin.py` | admin gate, channel/video updates, recorded shell dispatch |
| `test_video_api.py`, `test_player.py`, `test_archive.py` | player endpoints, view counter, source choice, archive.org |
| `test_sitemap_feeds.py`, `test_listings.py`, `test_pages.py` | sitemaps, feeds, listings, pagination helper |
| `test_pagination.py` | page 2+ of search, channel, history and watch-later routes (page size set to 1) |
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

## Coverage by blueprint

Gate = an anonymous (or non-admin) request is refused. Happy = the normal case is
asserted on content or database state, not only on the status code. Fail = a bad input,
unknown id or refused action is asserted. "n/a" = the blueprint has no gate.
Checked 2026-10-31 by grepping every route's literal path against `tests/`
(everything is referenced except the rows under "Gaps") and by mutation (below).

| Blueprint | Gate | Happy | Fail | Notes |
|---|---|---|---|---|
| `auth` | yes | yes | yes | `/register` is tested with Turnstile stubbed; OAuth `authorize`/`callback` are not tested (providers) |
| `video` | n/a | yes | yes | player, API, embed, ping-view, search |
| `channel` | n/a | yes | yes | page 2+ covered in `test_pagination.py` |
| `category` | n/a | yes | yes | |
| `playlist` | yes | yes | yes | list-full, duplicates, featured-video repair |
| `user` | yes | yes | yes | history and watch-later page 2+ covered in `test_pagination.py`; account delete with playlists is `xfail` |
| `settings` | yes | yes | yes | |
| `admin` | yes | yes | yes | shell-outs recorded, never run; `mass_email` and uploads excluded |
| `sitemap` | n/a | yes | yes | unknown channel feed is empty, not 404 (pinned on purpose) |
| `about`, `donate`, `newsletter`, `theme` | n/a | yes | n/a | static pages and the theme toggle |

No route is left without a test except the OAuth `authorize` and `callback` pair.

## Mutation check

Deliberately breaking the code should make a test fail. `scripts/mutation_check.py`
does it: each of its 17 breaks (the admin and login gates, the `loggedin` cookie
signature, expiry, path skip and mimetype check, `safe_next` host and `//` checks, list
cap and duplicates, the Swedish column, `valid_video_id`, page offsets in history and
search, and the registration Turnstile and welcome mail) is applied to a throwaway copy
on www2, and the suite runs on the legacy stack. `CAUGHT` is good; `MISSED` means a
test is missing. Nothing in this clone or the www2 checkouts is changed.

    scripts/mutation_check.py --list
    scripts/mutation_check.py --baseline   # the unchanged tree must pass first
    scripts/mutation_check.py [N ...]      # all, or by number; 30-100 s each

Do not run it at the same time as `run_both.sh` (both use the www2 test database). Run
it after a large change to one of those areas, and add a break to `MUTATIONS` when you
add a guard worth protecting. The first run on 2026-10-31 found two gaps (`safe_next`
with `////host`, the cookie path skip on an HTML response); both now have tests.

## Not covered

`mass_email`, `update_bounce` and `add_email_list` uploads (write files, send mail),
OAuth, the real Cloudflare Turnstile check (registration itself is tested with a stub), real S3/archive.org, and browser behaviour.

### Manual checklist after a change in these areas

- **Remember me:** log in with "remember me" in a real browser, close it, reopen it
  after the session lifetime, and check that you are still logged in (and logged out
  without the box). Behaviour differs between flask-login and ytac.
- **Registration:** the real Turnstile widget renders and passes, and a signup creates the
  user and sends the welcome mail (the stubbed flow is in `test_auth.py`).
- **OAuth:** Google and GitHub login round trip, both for a new and an existing user.
- **Mail:** a password reset and a confirmation mail arrive and their links work.
- **Admin tables:** the channel and video lists load, sort and save in a browser.
- **Uploads:** `mass_email`, bounce and email-list uploads on a copy, never on prod data.
- **Playback:** one IA video and one archived (non-IA) video play in a browser, with
  thumbnails through the proxy.
