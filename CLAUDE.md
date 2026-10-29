# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

altCensored.com — a Flask/PostgreSQL website that archives YouTube videos that have been censored or deleted, with Internet Archive integration.

## Running the development server

**The clone at `/home/lc/src/altcensored` lives on prod www and has no `.venv`; there is no dev server in this stack.** Don't point a dev server at the prod DB. Use prod's interpreter (`/opt/altcen/altcensored/venv/bin/python`) for offline checks such as importing modules or the Flask test client.

For a separate dev machine with its own database:

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

A long-lived branch, on all three remotes, that moves the app from `altcen-models` to the private `ytac` package (renamed columns, no `Entity`, `User` is `AltcenUser`, flask-login removed). Details, the column mapping and the ytac pin rules are in `docs/ytac-cutover.md`; read it before touching that branch. The short version:

- **After every master deploy**, merge master into it in the worktree `~/src/altcensored-ytac` (`git merge master`; never rebase or force-push), translate any new `ytc_*`/`Entity`/flask-login use to the ytac names, run `~/src/altcensored-ytac/.claude/check_ytac.sh` (must say PASS), then commit and push to all three remotes.
- Never merge it into master or deploy it as part of a sync; the cutover is its own decision.
- Scope: this session covers altcensored branches only. The `ytac` and `ytac-archive` repos belong to a separate session; reading them is fine, changing them is not.

## Testing

This repo has no tests; manual testing against the database is the only option. The `ytac-cutover` branch has the check script (see above). The `ytac` package has its own pytest suite in the private `altCensored/ytac` repo, covering that package and not this app's pages. Its integration tests in `tests/integration/` run only when `YTAC_TEST_DATABASE_URL` is set and they create and **drop every table** in that database, so never point them at a real database.

## Architecture

Describes `master`. On `ytac-cutover` the model layer differs (see `docs/ytac-cutover.md`).

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

One flat module per feature in `alt2/`, each with its own blueprint registered in `create_app()` (`video`, `channel`, `admin`, `auth/` sub-package, `category`, `language`, `playlist`, `user`, `settings`, `newsletter`, `donate`, `sitemap`, `about`, `theme`). Templates mirror this under `alt2/templates/<blueprint_name>/`.

### Caching pattern

`alt2/util.py` centralises all cached database queries. Functions like `videos_newest()`, `channels_deleted()`, `channeli()` are decorated with `@cache.cached()` or `@cache.memoize()`. Session variables (videocount, channelcount, etc.) are populated from these cached functions on first access, avoiding repeated DB hits per request. The cache TTL is 3600 s (1 hour) by default.

### Session/preferences

User preferences (locale, theme, playnext, autoplay, looplist) and navbar translations live in Flask's server-side session, initialised on first access by `util.py` helpers (`get_locale()`, `get_theme()`, …). `login_user_altcen()` / `logout_user_altcen()` sync the session to the `altcen_user.settings` JSON column.

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

### Template filters and access control

Jinja filters are defined in `alt2/__init__.py`. The decorators in `util.py` (`login_required`, `admin_login_required`, `email_verified_required`, `contributor_required`) are plain function decorators, not Flask-Login's; they check `session['user']`.
