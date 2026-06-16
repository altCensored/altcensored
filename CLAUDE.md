# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

altCensored.com — a Flask/PostgreSQL website that archives YouTube videos that have been censored or deleted, with Internet Archive integration.

## Running the development server

Requires a local or remote PostgreSQL database named `altcen` and a Redis server running with defaults. Set required environment variables (see `alt2/config.py` for the full list), then:

```bash
. .venv/bin/activate
export FLASK_APP=alt2
export FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5000
```

Key env vars at minimum:
- `ALTC_DATABASE_URL` — e.g. `postgresql+psycopg2://user:pass@127.0.0.1/altcen`
- `ALTC_SECRET_KEY` — any string
- `CACHE_REDIS_HOST` — e.g. `localhost`
- `RANDOM_VALUE` — any string (used as an anti-scraping token in templates)

Production runs as gunicorn behind nginx (no Docker). The `docker-compose.yml` is for local dev only.

## Development workflow

1. **Before making any changes**, create a new local branch: `git checkout -b <short-descriptive-name>`
2. **Make all changes and commit on that branch.** Never commit directly to `master` or `main`.
3. **Wait** — do not push the branch or merge to master. The user tests locally against the running Flask dev server.
4. **When the user says "tested, now merge push commit"** (or equivalent confirmation), merge the branch into master and push to all three remotes:
   ```bash
   git checkout master
   git merge <branch-name>
   git push github HEAD
   git push bbucket_key HEAD
   git push codeberg HEAD
   ```
5. Do not merge or push until the user explicitly confirms testing is done.

The three remotes are:
- `github` — git@github.com:altCensored/altcensored.git
- `bbucket_key` — git@bitbucket.org:altcensored/altcensored.git
- `codeberg` — git@codeberg.org:altcensored/altcensored.git

## No test suite

There are no tests. Manual testing against the database is the only option.

## Architecture

### Application factory

`alt2/__init__.py` contains `create_app()`. It wires all blueprints, registers Jinja2 template filters, configures Flask-Talisman (CSP), Flask-BabelPlus (i18n), Flask-Login, Flask-Caching (Redis), and Flask-WTF (CSRF).

### Database layer

`alt2/database.py` creates a raw SQLAlchemy engine with a scoped session (`db_session`). There is **no Flask-SQLAlchemy** — all queries use `db_session` directly or via `Model.query`.

`alt2/models.py` defines all models:
- `Entity` — polymorphic base table; `Video` and `Source` both inherit from it via joined-table inheritance
- `Source` — a YouTube channel (has `ytc_id`, archive flags, sync scheduling via `delta`/`next`)
- `Video` — a single video; linked to `Source` via the `content` join table (`Sources_to_Videos`)
- `Mv_Video`, `Mv_Channel`, `Mv_Category`, `Mv_Playlist`, `Mv_Altcen_user` — **PostgreSQL materialized views**, modeled as read-only ORM classes. Use these for all reads; never write to them directly. They are refreshed externally by a separate scraper process.
- `User` — site users; stores settings/preferences as JSON, watched/watchlater as `ARRAY(String)`
- `Playlist`, `Vpn_conn`, `Vpn_node`, `Crypto`, `Email_list`, etc. — supporting tables

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

Videos that are deleted on YouTube may be archived at `archive.org/details/youtube-<video_id>`. `util.get_ia_item()` fetches IA metadata and populates `videofile`/`thumbnail` on the `Entity` row. The `exists_ia` / `exists_ac` flags on `Entity` / `Mv_Video` control which player is shown.

### Custom image proxying

Thumbnail URLs are served through internal proxy paths (`IPROXY`, `IPROXYBIG`, `IPROXYHUGE`, `ACIPROXY`) to avoid hotlinking YouTube's CDN directly. These are configured as env vars.

### Jinja2 template filters

Defined in `alt2/__init__.py`: `viewdisplay` (compact K/M/B), `commafy`, `hourminsec`, `datetimeformat`, `ia_fname` (IA-safe filename), `linkify`, `nl2br`, `time_diff`, `iso8601duration`.

### Access control decorators

Defined in `util.py`: `login_required`, `admin_login_required`, `email_verified_required`, `contributor_required` — all are plain function decorators (not Flask-Login's), checking `session['user']`.
