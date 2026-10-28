# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

altCensored.com — a Flask/PostgreSQL website that archives YouTube videos that have been censored or deleted, with Internet Archive integration.

## Running the development server

For a dev machine with its own database. There is no dev server in this stack: the clone at `/home/lc/src/altcensored` lives on prod www and has no `.venv`. There, use prod's interpreter (`/opt/altcen/altcensored/venv/bin/python`) for offline checks such as importing modules or the Flask test client, and don't point a dev server at the prod DB.

Requires a local or remote PostgreSQL database named `altcen` and a Redis server running with defaults. Set required environment variables (see `alt2/config.py` for the full list), then:

```bash
. .venv/bin/activate   # your own virtualenv with requirements.txt installed
export FLASK_APP=alt2
export FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5000
```

Key env vars at minimum:
- `ALTC_DATABASE_URL` — e.g. `postgresql+psycopg2://user:pass@127.0.0.1/altcen`
- `ALTC_SECRET_KEY` — any string
- `CACHE_REDIS_HOST` — e.g. `localhost`
- `RANDOM_VALUE` — any string (used as an anti-scraping token in templates)
- `ALTC_LOGGEDIN_SECRET` — signs the `loggedin` cookie (`<expires>.<base64url md5("<expires> <secret>")>`, nginx `secure_link` format). Must match the secret in nginx's `secure_link_md5` include, which exempts logged-in users from anon rate limits. If unset, the old unsigned random cookie is issued.

Production runs as gunicorn behind nginx (no Docker) on www, from the checkout at `/opt/altcen/altcensored` (its venv is `venv/`, not `.venv/`). The `docker-compose.yml` is for local dev only.

Deploying to production (after merge + push):

```bash
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored status --short   # must be clean
sudo -n git -c safe.directory=/opt/altcen/altcensored -C /opt/altcen/altcensored pull --ff-only origin master
sudo -n systemctl reload gunicorn   # graceful SIGHUP: workers re-spawn with the new code
```

These exact forms are pre-approved for Claude in the gitignored `.claude/settings.local.json` on www; other spellings prompt. Then smoke-test over the socket: `curl --unix-socket /run/gunicorn.sock -H 'Host: altcensored.com' -H 'X-Forwarded-Proto: https' http://localhost/...` (without the proto header the app redirects to https).

A reload does not pick up changes to `/opt/altcen/altcensored.env`: the workers inherit the master's environment. After adding or changing an env var, use `sudo systemctl restart gunicorn`.

## Development workflow

1. **Before making any changes**, create a new local branch: `git checkout -b <short-descriptive-name>`
2. **Make all changes and commit on that branch.** Never commit directly to `master` or `main`.
3. **Wait** — do not push the branch or merge to master until the user has tested it.
4. **When the user says "tested, now merge push commit"** (or equivalent confirmation), merge the branch into master and push to all three remotes:
   ```bash
   git checkout master
   git merge <branch-name>
   git push github HEAD
   git push bbucket_key HEAD
   git push codeberg HEAD
   ```
5. Do not merge or push until the user explicitly confirms testing is done.
6. **Deploying is a separate step.** "Merge push commit" does not include it. Deploy (see "Deploying to production" above) when the user asks for it, e.g. "deploy" or "tested, do it".

The three remotes are:
- `github` — git@github.com:altCensored/altcensored.git
- `bbucket_key` — git@bitbucket.org:altcensored/altcensored.git
- `codeberg` — git@codeberg.org:altcensored/altcensored.git

## `ytac-cutover` branch (planned deploy by ~2027-04)

A long-lived branch, on all three remotes, that moves the app from `altcen-models` to the private `ytac` package. The new schema renames columns: `ytc_deleted` → `deleted`, `ytc_deleteddate` → `deleted_date`, `ytc_subscribercount` → `channel_follower_count`, `ytc_id` → `extractor_data`, and so on. There is no `Entity`, `User` is `AltcenUser`, and flask-login is removed. Keep it current with master:

- **After every master deploy**, merge master into it in the worktree `~/src/altcensored-ytac`: `git merge master`. Always merge, never rebase or force-push. `rerere` is enabled, so resolved conflicts are reapplied.
- A change that merges cleanly can still be wrong there. Translate any new `ytc_*` column access, `Entity` use or flask-login call to the ytac names.
- Run `~/src/altcensored-ytac/.claude/check_ytac.sh`. It must say PASS. It compiles the code, flags new altcen-models leftovers and conflict markers, and runs the test client against orcl's `ytac` DB as read-only `claude_ro`, with an in-memory cache, so prod Redis and data are untouched. Known pre-existing failures are listed in `.claude/known_bad_pages.txt` and `.claude/leftovers_baseline.txt` there.
- Commit the merge and push the branch to all three remotes. Never merge it into master or deploy it as part of a sync; the cutover is its own decision.

References in the private `altCensored/ytac` repo. Read them with `gh api repos/altCensored/ytac/contents/<path> -H 'Accept: application/vnd.github.raw'`; links won't work for public readers.
- `YTAC_CUTOVER.md` has the full old → new column mapping for every materialized view. It covers columns only: the ytac models also dropped relationships the old ones had. For example, `MvPlaylist.user` is re-added on the branch in `alt2/models.py`.
- `tests/` is ytac's own pytest suite. It covers the ytac package (config, sources, videos, yt-dlp handling), not this app's pages. The integration tests in `tests/integration/` run only when `YTAC_TEST_DATABASE_URL` is set, and they create and **drop every table** in that database. Never point them at a real database.

## No test suite

This repo has no tests; manual testing against the database is the only option. The `ytac` package has its own suite (see above), and the `ytac-cutover` branch has the check script.

## Architecture

### Application factory

`alt2/__init__.py` contains `create_app()`. It wires all blueprints, registers Jinja2 template filters, configures Flask-Talisman (CSP), Flask-BabelPlus (i18n), Flask-Login, Flask-Caching (Redis), and Flask-WTF (CSRF).

### Database layer

`alt2/database.py` creates a raw SQLAlchemy engine with a scoped session (`db_session`). There is **no Flask-SQLAlchemy** — all queries use `db_session` directly or via `Model.query`.

Models live in the external `altcen-models` package (`altcen_models.db`); `alt2/models.py` re-exports them and adds app-side helpers. A `before_flush` guard in `altcen_models/db.py` makes writes to materialized-view models a hard error.
- `Entity` — polymorphic base table; `Video` and `Source` both inherit from it via joined-table inheritance
- `Source` — a YouTube channel (has `ytc_id`, archive flags, sync scheduling via `delta`/`next`)
- `Video` — a single video; linked to `Source` via the `content` join table (`Sources_to_Videos`)
- `MvVideo`, `MvChannel`, `MvCategory`, `MvPlaylist`, `MvAltcenUser` — **PostgreSQL materialized views**, modeled as read-only ORM classes. Use these for all reads; never write to them directly. They are refreshed externally by a separate scraper process.
- `User` — site users; stores settings/preferences as JSON, watched/watchlater as `ARRAY(String)`
- `Playlist`, `VpnConn`, `VpnNode`, `Crypto`, `EmailList`, `Category`, `Language`, `Translation`, `Counter` — supporting tables (`VpnConn`/`VpnNode` are defined in `altcen_models` but not re-exported by `alt2/models.py`)

### Blueprint layout

Each feature is a flat module in `alt2/` with its own blueprint, registered in `create_app()`:
- `video.bp` — home page, video player, search (`/`, `/channel/<id>/video/<id>`, etc.)
- `channel.bp` — channel listings and individual channel pages (`/channel/...`)
- `admin.bp` — admin panel at `/admin`
- `auth/` (sub-package) — login/register/OAuth at `/auth`
- `category`, `language`, `playlist`, `user`, `settings`, `newsletter`, `donate`, `sitemap`, `about`, `theme` — each a separate blueprint

Templates mirror this structure under `alt2/templates/<blueprint_name>/`.

### Caching pattern

`alt2/util.py` centralises all cached database queries. Functions like `videos_newest()`, `channels_deleted()`, `channeli()` are decorated with `@cache.cached()` or `@cache.memoize()`. Session variables (videocount, channelcount, etc.) are populated from these cached functions on first access, avoiding repeated DB hits per request. The cache TTL is 3600 s (1 hour) by default.

### Session/preferences

User preferences (locale, theme, playnext, autoplay, looplist) and navbar translations are stored in Flask's server-side session. `util.py` helpers (`get_locale()`, `get_theme()`, etc.) initialise session keys on first access. On login/logout, `login_user_altcen()` / `logout_user_altcen()` sync the session to the `altcen_user.settings` JSON column.

### Internationalisation

Flask-BabelPlus with 8 languages: `en, de, es, fr, pt, nl, it, se`. UI strings are also stored in the `translation` DB table and served per-session locale via `get_navtabs()`. `.po`/`.mo` files live in `alt2/translations/`. To extract/compile translations:

```bash
pybabel extract -F alt2/babel.cfg --keyword=_l -o alt2/messages.pot alt2/
pybabel update -i alt2/messages.pot -d alt2/translations
pybabel compile -d alt2/translations
```

### Internet Archive integration

Videos that are deleted on YouTube may be archived at `archive.org/details/youtube-<video_id>`. `util.get_ia_item()` fetches IA metadata and populates `videofile`/`thumbnail` on the `Entity` row. The `exists_ia` / `exists_ac` flags on `Entity` / `MvVideo` control which player is shown.

### Custom image proxying

Thumbnail URLs are served through internal proxy paths (`IPROXY`, `IPROXYBIG`, `IPROXYHUGE`, `ACIPROXY`) to avoid hotlinking YouTube's CDN directly. These are configured as env vars.

### Jinja2 template filters

Defined in `alt2/__init__.py`: `viewdisplay` (compact K/M/B), `commafy`, `hourminsec`, `datetimeformat`, `ia_fname` (IA-safe filename), `linkify`, `nl2br`, `time_diff`, `iso8601duration`.

### Access control decorators

Defined in `util.py`: `login_required`, `admin_login_required`, `email_verified_required`, `contributor_required` — all are plain function decorators (not Flask-Login's), checking `session['user']`.
