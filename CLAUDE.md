# CLAUDE.md

Guidance for Claude Code in this repo (`master` and branches off it). altCensored.com is a Flask/PostgreSQL site that archives censored or deleted YouTube videos, with Internet Archive (IA) integration. It runs on the private `ytac` package and the `ytac` database (live since 2026-10-31). There is one branch, `master`. The old `altcen-models` code and the `ytac-cutover` branch are gone; the old schema survives only in git history.

## Read this first

- **Production = node www, database `ytac`** (on www's PostgreSQL; read with `psql service=ytac-www`). The old `altcen` database is not used by the app.
- The app is gunicorn behind nginx on www, from the root-owned checkout `/opt/altcen/altcensored` (branch `master`, venv `venv/`). The systemd drop-in `gunicorn.service.d/ytac.conf` points gunicorn at that checkout, its venv and the env file `/opt/altcen/altcensored.env`. nginx serves static files and its error pages (`400/403/404/429/500.html`, `maintenance.html`) from the same checkout (`root /opt/altcen/altcensored/alt2/static`), so one pull updates both. No Docker. `docker-compose.yml` and `web.Dockerfile` are for a separate dev machine only and do not install ytac.
- **Renamed 2026-11-01:** the checkout was `/opt/altcen/altcensored-ytac` and its env `/opt/altcen/altcensored-ytac.env` until then. The pre-cutover checkout is kept at `/opt/altcen/altcensored-legacy` and the legacy env (its `ALTC_DATABASE_URL` names the old `altcen` DB) at `/opt/altcen/altcensored-legacy.env`; neither is used by the app. Only the yt-syncac units (`yts@`, `yts_sync@`, `ytsmaint`, timers disabled) load the legacy env, so a manual yt-syncac run can never hit `ytac`. `ytac-archive_*`, `restic_backup` and the admin buttons' shell-outs load `altcensored.env` (they don't read `ALTC_DATABASE_URL`). Backups of the pre-rename files: `/root/envswap-20261101/`, `/root/ytac.conf.bak-20261101-rename`.
- **Error pages:** the app renders its own 400/404/429/500/503 (`video/*.html` templates). nginx's `error_page 500 502 503 504 /500.html` covers only nginx's own errors (gunicorn down, timeouts), and **not** in the Anubis-checked locations (`/`, `/watch`, `/page/N`, `/search`): those set their own `error_page 401/403`, so they don't inherit the server's 5xx line and show nginx's bare built-in page. Maintenance mode: `touch /opt/altcen/MAINTENANCE` (no reload) serves `maintenance.html` as a 503. nginx doesn't log 503 or 444 to `access.log`, so maintenance traffic is invisible there.
- **Tests** live in `tests/` (pytest, a real app against a seeded PostgreSQL). They run on **www2**, never on www: they need a dedicated database whose name ends in `_test` and **drop every table** in it. Command and layout are in `tests/README.md`; `tests/run_www2.sh` runs them on www2 (it fetches the branch there, so push first). They cover the public pages, login and the access decorators, playlists, watch later and history, settings, admin (shell-outs are recorded, never run), sitemaps and feeds, the player and view counter, the archive.org lookup, cache and rate limits, error pages and the translation catalogs. Not covered: `mass_email` and the bounce/email-list uploads, OAuth, Turnstile, real S3 and archive.org calls, and anything needing a browser. The suite's seed and schema helpers still know the old altcen-models schema; only the ytac one is run. `scripts/mutation_check.py` still points at the retired legacy venv and needs retargeting before use. `scripts/parity_player.py` and `scripts/parity_views.py` compared the legacy and ytac databases for the cutover and are history now.
- Video playback is the site's core purpose. Treat any video-serving fault as top priority, and follow the "one change at a time" rule in the global `CLAUDE.md`.

## Workflow

1. Before any change, `git checkout -b <short-name>`. Never commit directly to `master`.
2. Commit on that branch. Do not push or merge until the user has tested it.
3. On "tested, now merge push commit" (or equivalent), merge into `master` and push to all three remotes: `git push github HEAD`, `git push bbucket_key HEAD`, `git push codeberg HEAD`. The remotes are `git@github.com:altCensored/altcensored.git`, `git@bitbucket.org:altcensored/altcensored.git` and `git@codeberg.org:altcensored/altcensored.git`.
4. **Deploying is a separate step**, done only when the user asks ("deploy", "tested, do it"). Merge and push do not include it.

## Deploying

Run each command as its own Bash call:

```bash
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored status --short   # must be clean
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored pull --ff-only origin master
sudo -n systemctl reload gunicorn
```

- These spellings may prompt until they are added to the gitignored `.claude/settings.local.json`.
- `reload` is a graceful SIGHUP and picks up code only. It does **not** pick up `/opt/altcen/altcensored.env`: after an env change, or a change of the ytac package in the venv, use `sudo -n systemctl restart gunicorn`.
- "Worker was sent SIGTERM" and "reentrant call inside stderr" log lines after a reload are benign.
- Smoke-test over the socket, because without the proto header the app redirects to https:
  `curl --unix-socket /run/gunicorn.sock -H 'Host: altcensored.com' -H 'X-Forwarded-Proto: https' http://localhost/...`

## ytac package (no pin)

- `requirements.txt` has no ytac line. ytac is installed in the venv outside this repo, so `pip list | grep ytac` in `/opt/altcen/altcensored/venv` says which version runs.
- ytac uses date versions (`YYYY.M.D.N`) and auto-tags every push, so a newer tag is **not** a reason to upgrade. Change the installed version only when the ytac session asks in `~/src/ytac/.claude/HANDOVER-altcensored.md` **and** the user agrees, then restart gunicorn.
- ytac needs psycopg 3 and SQLAlchemy 2.1 or newer, alongside psycopg2.
- Scope: this session covers altcensored only. The `ytac` and `ytac-archive` repos belong to a separate session: reading them is fine, changing them is not. Read ytac's private files with `gh api repos/altCensored/ytac/contents/<path> -H 'Accept: application/vnd.github.raw'`. `YTAC_CUTOVER.md` there has the old → new column mapping for every materialized view.
- Handover rules are only in the global `~/.claude/CLAUDE.md`.

## Database

- Models come from `ytac.db`; `alt2/models.py` re-exports them with `AltcenUser as User`. There is no `Entity`: `Video` and `Source` are plain tables and the join table is `content_table`. ytac has two registries, `Base` and `MvBase` (materialized views); `alt2/database.py` gives both `.query`.
- Columns were renamed in the cutover, for example `ytc_deleted` → `deleted`, `ytc_deleteddate` → `deleted_date`, `ytc_subscribercount` → `channel_follower_count`, `ytc_id` → `extractor_data`, `exists_ia` → `ia_exists`, `exists_ac` → `ac_exists`. A video's channel is `MvVideo.source_extractor_data`; the app uses it only as a join key to the channel.
- `EmailList` uses `subscribed`, `last_sent`, `source`, `action`, `created`, but `AltcenUser` kept its `email_*` names. Code that touches both must branch on the model; a mismatch can silently fail to save.
- ytac provides `MvPlaylist.user` and the materialized-view write guard. Never re-add either in `alt2/models.py`. Never write to an `Mv*` model: it is a hard error.
- `alt2/database.py` builds a raw SQLAlchemy engine and a gevent-scoped `db_session`. There is **no Flask-SQLAlchemy**. psycopg is made gevent-friendly with `psycogreen`. Keep any DB URL in the explicit `postgresql+psycopg2://` form (a bare `postgresql://` means psycopg 3 under SQLAlchemy 2.1).
- Reads: `psql service=ytac-www` (read-only `claude_ro`). The `ytac-*-rw` services exist for orcl and www2 only; for a write on www ask the user. Don't read `ALTC_DATABASE_URL` from the env file.
- Before a DB write: back up the affected rows to `~/` with `\copy`, dry-run in a transaction with `ROLLBACK`, then apply in a `DO` block that raises unless `ROW_COUNT` matches the expected count.
- Pages read **materialized views**, refreshed by ytac's `ytac_refresh` timer, so DB edits show only after the next refresh. Search uses GIN indexes on each view's `document` column; they are created in ytac's `views.py`.
- Stored featured-video dicts may still carry legacy keys, so `video_thumb_url()` in `alt2/__init__.py` reads both the old and new names.
- Schema changes are made in the ytac package, not here. `migrations/` holds the old altcen-models SQL files, kept as history only.

## Safety

- **Never run the app against prod Redis or the prod DB.** `alt2/config.py` hardcodes Redis DB 1, the same DB production uses for its cache and rate limiter.
- `scripts/check_ytac.sh` is the supported offline check. It uses orcl's `ytac` DB as read-only `claude_ro` (`service=ytac-orcl`), an in-memory cache and an unreachable Redis host, and refuses any other cache backend. It needs a `.venv` in the repo root, and it must say PASS. It compiles the code, looks for conflict markers and new leftovers of the old code, loads about 20 pages through the Flask test client, scans every `Model.attribute` against the ytac models, and exercises the email helpers. Baselines are in `scripts/ytac_check/`: don't rebaseline to hide a new failure.
- ytac's `tests/integration/` creates and **drops every table** in `YTAC_TEST_DATABASE_URL`. Only point it at a throwaway DB.

## App structure

- `alt2/__init__.py` holds `create_app()`: blueprints, Jinja filters, Flask-Talisman (CSP with script nonces), Flask-BabelPlus, Flask-WTF (CSRF), Flask-Limiter (Redis), and Flask-Caching. flask-login is not used.
- One flat module per feature in `alt2/` (`video`, `channel`, `admin`, `category`, `language`, `playlist`, `user`, `settings`, `newsletter`, `donate`, `sitemap`, `about`, `theme`, plus the `auth/` package), each with its own blueprint registered in `create_app()`. Templates mirror this under `alt2/templates/<blueprint>/`. `alt2/services/` has the IA archive and email helpers.
- `alt2/config.py` reads everything from env vars. Minimum for a local run: `ALTC_DATABASE_URL`, `ALTC_SECRET_KEY`, `CACHE_REDIS_HOST`, `RANDOM_VALUE` (anti-scraping token used in templates). Prod's env file is `/opt/altcen/altcensored.env`.
- **Caching:** `alt2/util.py` centralises the cached queries with `@cache.cached()` or `@cache.memoize()`. TTL is 3600 s, in Redis DB 1, which is also the rate limiter's store. Session counters (videocount, channelcount) fill from these on first access.
- **Session and preferences:** locale, theme, playnext, autoplay, looplist and the navbar translations live in Flask's server-side session, initialised by `util.py` helpers (`get_locale()`, `get_theme()`, ...). `login_user_altcen()` and `logout_user_altcen()` sync the session with the `altcen_user.settings` JSON column.
- **Access control:** `login_required` and `admin_login_required` in `util.py` are plain decorators that check `session['user']`. Email verification is checked inline in the auth routes (`user.email_verified`), not by a decorator.
- **`loggedin` cookie:** nginx uses it to exempt logged-in users from anon rate limits. It is signed (`<expires>.<base64url md5("<expires> <secret>")>`, nginx `secure_link` format) with `ALTC_LOGGEDIN_SECRET`, which must equal the secret in nginx's `secure_link_md5` include. If the secret is unset, an old unsigned 64-hex cookie is issued. When rotating the secret, change both files and **restart** gunicorn. Helpers are `make_loggedin_cookie`, `loggedin_cookie_valid` and `set_loggedin_cookie` in `util.py`. The `refresh_loggedin_cookie` hook skips `/feed`, `/sitemap*`, `/ip/` and `/acip/`, because nginx caches those and a cookie there would leak to everyone.
- **i18n:** 8 languages (`en de es fr pt nl it sv`). UI strings also live in the `translation` table, served per session locale by `get_navtabs()`. The table's Swedish column is still named `se`, so `util.translation_column()` maps `sv` to it, and a stored or session `se` is read as `sv`. Update the translations with:
  ```bash
  pybabel extract -F alt2/babel.cfg --keyword=_l -o alt2/messages.pot alt2/
  pybabel update --no-fuzzy-matching -i alt2/messages.pot -d alt2/translations
  pybabel compile -d alt2/translations
  ```
- **Internet Archive:** a deleted video may exist at `archive.org/details/youtube-<video_id>`. `get_ia_item()` in `alt2/services/archive.py` fetches the IA metadata (cached in Redis for 30 days on a hit) and fills `videofile` and `thumbnail`. The `ia_exists` and `ac_exists` flags choose the player. A missing or `None` `ia_exists` means unknown, so only an explicit `False` means "not on IA". `video_thumb_url()` in `__init__.py` picks the thumbnail source.
- **Image proxying:** thumbnails go through the internal proxy prefixes (`IPROXY`, `IPROXYBIG`, `IPROXYHUGE`, `ACIPROXY`, set by env var) so YouTube's CDN is never hotlinked.
