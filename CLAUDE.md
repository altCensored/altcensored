# CLAUDE.md

Guidance for Claude Code in this repo (`master` and branches off it). The `ytac-cutover` branch, checked out in the worktree `~/src/altcensored-ytac`, has its own `CLAUDE.md`.

altCensored.com is a Flask/PostgreSQL site that archives censored or deleted YouTube videos, with Internet Archive (IA) integration.

## Read this first

- **This clone is on prod www.** `/home/lc/src/altcensored` has no `.venv` and there is no dev server in this stack. Never point a dev server at the prod DB. For offline checks use prod's interpreter, `/opt/altcen/altcensored/venv/bin/python` (import modules, or the Flask test client).
- **Production** is gunicorn behind nginx, with no Docker, from the root-owned checkout `/opt/altcen/altcensored` (venv `venv/`). `docker-compose.yml` is for a separate dev machine only.
- **Tests** live in `tests/` (pytest, a real app against a seeded PostgreSQL). They run on **www2**, never here: they need a dedicated database whose name ends in `_test` and **drop every table** in it. See `tests/README.md` for the command. The same suite runs on master and on `ytac-cutover`. They cover the public pages, login and the access decorators, playlists, watch later and history, settings, admin (shell-outs are recorded, never run), sitemaps and feeds, the player and view counter, the archive.org lookup, cache and rate limits, error pages and the translation catalogs. Not covered: `mass_email` and the bounce/email-list uploads (they write files and send mail), OAuth, Turnstile, real S3 and archive.org calls, and anything needing a browser. Use `tests/run_both.sh` to run master and `ytac-cutover` on www2 (it `git pull`s the two checkouts there, so push first, or pass `--local` for uncommitted tests). `scripts/mutation_check.py` breaks the guard code on a scratch copy on www2 and checks that a test fails; run it after changing the access gates, the `loggedin` cookie, `safe_next`, list limits or pagination, and never together with `run_both.sh` (they share the test database). `scripts/parity_player.py` compares playback data and `scripts/parity_views.py` the channel, category, playlist and user views between the legacy and ytac databases (read-only; run them right after the real import, a stale snapshot makes them noisy). The private `ytac` package has its own suite, and its `tests/integration/` also **drops every table** in `YTAC_TEST_DATABASE_URL`, so never point that at a real database.
- Video playback is the site's core purpose. Treat any video-serving fault as top priority, and follow the "one change at a time" rule in the global `CLAUDE.md`.

## Workflow

1. Before any change, `git checkout -b <short-name>`. Never commit directly to `master`.
2. Commit on that branch. Do not push or merge until the user has tested it.
3. On "tested, now merge push commit" (or equivalent), merge into `master` and push to all three remotes: `git push github HEAD`, `git push bbucket_key HEAD`, `git push codeberg HEAD`. The remotes are `git@github.com:altCensored/altcensored.git`, `git@bitbucket.org:altcensored/altcensored.git` and `git@codeberg.org:altcensored/altcensored.git`.
4. **Deploying is a separate step**, done only when the user asks ("deploy", "tested, do it"). Merge and push do not include it.
5. After every deploy, sync `ytac-cutover` (see the last section).

## Deploying

Run each command as its own Bash call, in exactly these spellings (pre-approved in the gitignored `.claude/settings.local.json`; other spellings prompt):

```bash
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored status --short   # must be clean
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored pull --ff-only origin master
sudo -n systemctl reload gunicorn
```

- `reload` is a graceful SIGHUP and picks up code only. It does **not** pick up `/opt/altcen/altcensored.env`: after an env change use `sudo -n systemctl restart gunicorn`.
- "Worker was sent SIGTERM" and "reentrant call inside stderr" log lines after a reload are benign.
- Smoke-test over the socket, because without the proto header the app redirects to https:
  `curl --unix-socket /run/gunicorn.sock -H 'Host: altcensored.com' -H 'X-Forwarded-Proto: https' http://localhost/...`

## Database

- Models come from the external `altcen-models` package (`altcen_models.db`), installed in prod's venv. `alt2/models.py` re-exports them and bolts on password and reset-token helpers for `User`.
- `alt2/database.py` builds a raw SQLAlchemy engine and a gevent-scoped `db_session`. There is **no Flask-SQLAlchemy**: queries use `db_session` or `Model.query`. psycopg is made gevent-friendly with `psycogreen`.
- Keep any DB URL in the explicit `postgresql+psycopg2://` form (a bare `postgresql://` means psycopg 3 under SQLAlchemy 2.1).
- Reads: `psql service=altc-www` (read-only `claude_ro`, pre-approved). Writes: `service=altc-www-rw` (prompts each time). Other services in `~/.pg_service.conf`: `altc-orcl`, `ytac-orcl`, `ytac-test-orcl`. Don't read `ALTC_DATABASE_URL` from the env file.
- Before a DB write: back up the affected rows to `~/` with `\copy`, dry-run in a transaction with `ROLLBACK`, then apply in a `DO` block that raises unless `ROW_COUNT` matches the expected count.
- Pages read **materialized views**, which a separate scraper refreshes, so DB edits show only after the next refresh. Never write to an `Mv*` model; `altcen_models` has a `before_flush` guard that makes it a hard error.
- Main models: `Entity` (polymorphic base of `Video` and `Source`, joined-table inheritance), `Source` (a channel: `ytc_id`, archive flags, sync scheduling via `delta` and `next`), `Video` (linked to `Source` through the `content` table `Sources_to_Videos`), `User` (settings as JSON, `watched` and `watchlater` as `ARRAY(String)`), and the read-only `MvVideo`, `MvChannel`, `MvCategory`, `MvPlaylist`, `MvAltcenUser`. Supporting: `Playlist`, `Category`, `Language`, `Translation`, `Counter`, `Crypto`, `EmailList`. `VpnConn` and `VpnNode` exist in `altcen_models` but `alt2/models.py` doesn't re-export them.
- Schema changes are SQL files in `migrations/`.

## App structure

- `alt2/__init__.py` holds `create_app()`: blueprints, Jinja filters, Flask-Talisman (CSP with script nonces), Flask-BabelPlus, Flask-Login, Flask-WTF (CSRF), Flask-Limiter (Redis), and Flask-Caching (Sentry is commented out).
- One flat module per feature in `alt2/` (`video`, `channel`, `admin`, `category`, `language`, `playlist`, `user`, `settings`, `newsletter`, `donate`, `sitemap`, `about`, `theme`, plus the `auth/` package), each with its own blueprint registered in `create_app()`. Templates mirror this under `alt2/templates/<blueprint>/`. `alt2/services/` has the IA archive and email helpers.
- `alt2/config.py` reads everything from env vars. Minimum for local work: `ALTC_DATABASE_URL`, `ALTC_SECRET_KEY`, `CACHE_REDIS_HOST`, `RANDOM_VALUE` (anti-scraping token used in templates). Prod's env file is `/opt/altcen/altcensored.env`.
- **Caching:** `alt2/util.py` centralises the cached queries (`videos_newest()`, `channels_deleted()`, `channeli()` and others) with `@cache.cached()` or `@cache.memoize()`. TTL is 3600 s, in Redis DB 1, which is also the rate limiter's store. Session counters (videocount, channelcount) fill from these on first access.
- **Session and preferences:** locale, theme, playnext, autoplay, looplist and the navbar translations live in Flask's server-side session, initialised by `util.py` helpers (`get_locale()`, `get_theme()`, ...). `login_user_altcen()` and `logout_user_altcen()` sync the session with the `altcen_user.settings` JSON column.
- **Access control:** `login_required` and `admin_login_required` in `util.py` are plain decorators that check `session['user']`. They are not Flask-Login's. Email verification is checked inline in the auth routes (`user.email_verified`), not by a decorator.
- **`loggedin` cookie:** nginx uses it to exempt logged-in users from anon rate limits. It is signed (`<expires>.<base64url md5("<expires> <secret>")>`, nginx `secure_link` format) with `ALTC_LOGGEDIN_SECRET`, which must equal the secret in nginx's `secure_link_md5` include. If the secret is unset, an old unsigned 64-hex cookie is issued. When rotating the secret, change both files and **restart** gunicorn. Helpers are `make_loggedin_cookie`, `loggedin_cookie_valid` and `set_loggedin_cookie` in `util.py`. The `refresh_loggedin_cookie` hook skips `/feed`, `/sitemap*`, `/ip/` and `/acip/`, because nginx caches those and a cookie there would leak to everyone.
- **i18n:** 8 languages (`en de es fr pt nl it sv`). UI strings also live in the `translation` table, served per session locale by `get_navtabs()`. The table's Swedish column is still named `se` (altcen-models, ytac), so `util.translation_column()` maps `sv` to it, and a stored or session `se` is read as `sv`. Update the translations with:
  ```bash
  pybabel extract -F alt2/babel.cfg --keyword=_l -o alt2/messages.pot alt2/
  pybabel update --no-fuzzy-matching -i alt2/messages.pot -d alt2/translations
  pybabel compile -d alt2/translations
  ```
- **Internet Archive:** a deleted video may exist at `archive.org/details/youtube-<video_id>`. `get_ia_item()` in `alt2/services/archive.py` fetches the IA metadata (cached in Redis for 30 days on a hit) and fills `videofile` and `thumbnail`. The `exists_ia` and `exists_ac` flags choose the player. A missing or `None` `exists_ia` means unknown, so only an explicit `False` means "not on IA". `video_thumb_url()` in `__init__.py` picks the thumbnail source.
- **Image proxying:** thumbnails go through the internal proxy prefixes (`IPROXY`, `IPROXYBIG`, `IPROXYHUGE`, `ACIPROXY`, set by env var) so YouTube's CDN is never hotlinked.

## The `ytac-cutover` branch

A long-lived branch on all three remotes that moves the app to the private `ytac` package, to be deployed by about 2027-04. Read `docs/ytac-cutover.md` before touching it.

- After every master deploy, merge master into it in `~/src/altcensored-ytac` (never rebase or force-push), translate new `ytc_*`, `Entity` or flask-login use to the ytac names, run `scripts/check_ytac.sh` there (must say PASS), then commit and push to all three remotes.
- Never merge it into master or deploy it as part of a sync.
- **Scope:** this session covers altcensored branches only. The `ytac` and `ytac-archive` repos belong to another session: read them, don't change them. Handover rules are only in the global `~/.claude/CLAUDE.md`.
