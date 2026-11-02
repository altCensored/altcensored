# altCensored architecture

altCensored.com is a Flask site that indexes and plays censored or deleted YouTube videos. Video files come from the Internet Archive (IA) or from altCensored's own S3 store. The app is read-mostly: it displays data that other systems collect and does not scrape or download anything itself.

This document describes how the pieces fit together. Operational rules (deploying, safety, branch workflow) are in `CLAUDE.md`.

## System overview

```
                     browser
                        |
                  nginx (www)  ---- static files, error pages, rate limits,
                        |           Anubis checks, `loggedin` cookie exemption
                unix socket /run/gunicorn.sock
                        |
              gunicorn (gevent workers)
                        |
                 Flask app  alt2/
          +-------------+--------------+
          |             |              |
     PostgreSQL       Redis        external services
   (db `ytac`,     (DB 1: cache,   - archive.org (metadata, files)
   via ytac pkg)   rate limits)    - altCensored S3 / video server (MinIO)
                                   - image proxies (thumbnails)
                                   - mail (SES, SendGrid, Mailjet, SMTP)
```

Other systems share the database but are not part of this repo:

| System | Role |
|---|---|
| `ytac` package | Defines the schema and ORM models, owns migrations, and refreshes the materialized views (`ytac_refresh` timer). Installed in the venv, not pinned in `requirements.txt`. |
| `ytac-archive` | Downloads videos and uploads them to IA / S3, and sets the `ia_*` / `ac_exists` flags. |
| yt-syncac | Legacy sync workers (timers disabled). |

The app only reads the shared data, apart from user data (accounts, playlists, history) and a few per-video fields filled on demand (see [Playback](#playback)).

## Deployment

- Production is node `www`, database `ytac`. The code runs from `/opt/altcen/altcensored` (branch `master`, own venv), with settings from `/opt/altcen/altcensored.env`.
- gunicorn runs under systemd. nginx proxies to it and serves `alt2/static` and the static error pages straight from the same checkout.
- No Docker in production. `docker-compose.yml` and `web.Dockerfile` are for a separate dev machine.
- Tests run on `www2` only, against a scratch database (see `tests/README.md`).

## Repository layout

```
alt2/                 the Flask application package
  __init__.py         create_app(): extensions, hooks, blueprints, Jinja filters
  config.py           all configuration, read from environment variables
  database.py         SQLAlchemy engine and gevent-scoped session
  models.py           re-exports ytac models, adds password/token helpers to User
  cache.py            Flask-Caching instance
  util.py             cached queries, session/locale/theme helpers, access decorators,
                      `loggedin` cookie helpers
  pagination.py       pagination helper
  <feature>.py        one blueprint per feature (see below)
  auth/               login, register, password reset, OAuth (routes, forms, email)
  services/           archive.py (IA + S3 lookups), email.py (outbound mail)
  templates/          Jinja templates, one folder per blueprint, plus widgets/
  static/             css, js, images, flags, static error pages
  translations/       Babel catalogs (de es fr it nl pt sv); messages.pot is the template
tests/                pytest suite against a real app and seeded PostgreSQL
scripts/              check_ytac.sh (offline check), parity scripts, mutation check
altcen_sample_database_pg_dump.sql   sample data for local development
```

## Application core

`create_app()` in `alt2/__init__.py` builds the app in this order:

1. Load `alt2/config.py` (env-driven). Initialise Sentry if configured.
2. Set up extensions:
   - **Flask-Talisman**: security headers and a CSP with per-request script nonces.
   - **Flask-WTF** `CSRFProtect`: CSRF tokens on forms.
   - **Flask-Limiter**: rate limits, keyed by `client_ip()`, stored in Redis.
   - **Flask-Caching**: Redis cache, 3600 s default TTL.
   - **Flask-BabelPlus**: translations. **Flask-Mail** and **Flask-QRcode** are used for email and the donate page.
   - **MinIO client** (`app.minio_client`) for altCensored's S3.
3. Register Jinja filters and globals (time-ago, thumbnail URL helpers, text sanitising with `bleach`/`nh3`).
4. Install request hooks. `after_request` handles cache headers and the `loggedin` cookie. `teardown_appcontext` rolls back on error and removes the DB session.
5. Register error handlers (400, 404, 429, 500, 503) that render `templates/video/*.html`.
6. Register the blueprints.

Flask-Login is not used. Authentication is a plain `session['user']` check.

### Blueprints

| Blueprint | Prefix | Module | Purpose |
|---|---|---|---|
| video | `/` | `video.py` | Home, new/popular/latest lists, search, `/watch`, `/embed`, view-count and source APIs, play-next, RSS feeds |
| channel | `/channel` | `channel.py` | Channel lists (new, popular, deleted, limited, archived), channel pages, feeds, tables |
| category | `/category` | `category.py` | Category lists and per-category video lists |
| playlist | `/playlist` | `playlist.py` | Public and user playlists, create/edit/delete, add/remove video |
| user | `/user` | `user.py` | Public profile, history, watch later, user playlists |
| auth | `/auth` | `auth/` | Login, register, email confirmation, password reset, delete account, OAuth |
| settings | `/settings` | `settings.py` | Site settings (language, theme, playback) and account update |
| admin | `/admin` | `admin.py` | Channel and video management, mass email, bounce handling, system commands |
| sitemap | `/` | `sitemap.py` | `sitemap.xml` and its video, channel and static parts |
| theme | `/theme` | `theme.py` | Light/dark toggle |
| about, donate, newsletter | `/about`, `/donate`, `/newsletter` | one file each | Static-style pages |

`admin.py` is the largest module (about 950 lines). Several of its actions shell out to scripts on the server (resync, mirror, remove channel, and others). The tests record these calls and never run them.

## Data layer

- **Models come from ytac.** `alt2/models.py` re-exports `Video`, `Source`, `content_table`, `Category`, `Translation`, `Counter`, `AltcenUser as User`, `Playlist`, `EmailList` and `Crypto`, plus the read-only materialized-view models `MvVideo`, `MvChannel`, `MvCategory`, `MvPlaylist` and `MvAltcenUser`.
- **Two registries.** `Base` holds tables and `MvBase` holds materialized views. `database.py` gives both a `.query` property bound to the same session. ytac guards the `Mv*` models against writes.
- **Engine and session.** `database.py` builds a plain SQLAlchemy engine (pool 3 + 9 overflow, pre-ping, 1800 s recycle) and a `scoped_session` keyed by the current gevent greenlet. There is no Flask-SQLAlchemy. psycopg is made gevent-friendly with `psycogreen`. Database URLs must use the explicit `postgresql+psycopg2://` form.
- **Reads vs writes.** Listing, search and watch pages read the materialized views. These are refreshed by ytac on a timer, so new or changed rows show up only after the next refresh. Writes go to base tables: users, playlists, watch history and watch-later lists (stored on the user row), email lists, view counters, and the per-video fields filled by `get_ia_item()`.
- **Search** uses GIN indexes on each view's `document` column, created by ytac.
- **Schema changes** are made in ytac, not in this repo.

## Request lifecycle

```
nginx -> gunicorn -> Flask before/after hooks -> blueprint view
      -> util.py cached query (Redis) -> MvVideo / MvChannel / ... (PostgreSQL)
      -> Jinja template -> response
```

- **Caching.** Frequently used queries in `util.py` are wrapped with `@cache.cached()` or `@cache.memoize()` (3600 s, Redis DB 1). Session counters such as video and channel counts are filled from these on first access.
- **Rate limiting.** Flask-Limiter shares Redis DB 1. nginx also rate-limits anonymous traffic and exempts requests with a valid `loggedin` cookie.
- **Session and preferences.** Locale, theme, play-next, autoplay, loop-list and the navbar translations live in Flask's server-side session, initialised by `util.py` helpers. Login and logout sync the session with the user's `settings` JSON column.
- **Access control.** `login_required` and `admin_login_required` in `util.py` check `session['user']`. Email verification is checked inline in the auth routes.
- **`loggedin` cookie.** It is signed with `ALTC_LOGGEDIN_SECRET` in nginx's `secure_link` format so nginx can verify it. The secret must match the one in nginx's config. The refresh hook skips `/feed`, `/sitemap*`, `/ip/` and `/acip/` because nginx caches those responses and a cookie there would leak to other visitors.
- **Pagination.** Lists use `/…/page/<n>` routes and the helper in `pagination.py`.

## Playback

Playback is the site's core feature. `video.watch()` loads the `MvVideo` row, its channel and a "next up" list (a playlist, the user's history or watch-later, or the channel's earlier uploads). It then asks `_resolve_video_url()` for the media URL. The function tries these sources in order:

1. **altCensored S3** when `ac_exists` is truthy and `check_ac_object_exists()` confirms the object. The URL is `VIDEOSERVER_URL/<id>/<id>`.
2. **"Unavailable" placeholder** when the row has an IA flag saying the item is dark, restricted, login-gated or without video (`ia_dark`, `ia_restricted`, `ia_loggedin`, `ia_novideo`).
3. **IA file already known** from the `videofile` column, or derived from `thumbnail_ytdlp`. The URL is `IARCHIVEURL/<id>/<file>`.
4. **Unavailable** when `ia_exists is False`. A `None` value means unknown and falls through.
5. **Live IA lookup** with `services/archive.get_ia_item()`. It fetches `archive.org` metadata, picks the video and thumbnail files, and saves `videofile`, `thumbnail_ytdlp` or `ia_novideo` on the `Video` row. The result is cached in Redis with separate TTLs for hit, miss and failure (30 days on a hit).

For logged-in users, `watch()` also appends the video to the user's `watched` list. `/api/ping-view/<id>` counts views, and `/api/video-sources/<id>` serves the sources to the player (video.js). `/embed/<id>` is the embeddable player.

Thumbnails and channel images are never hotlinked from YouTube. They go through proxy prefixes (`IPROXY`, `IPROXYBIG`, `IPROXYHUGE`, `ACIPROXY`, ...) set by environment variables. `video_thumb_url()` in `__init__.py` picks the thumbnail source and still reads legacy key names in stored featured-video dicts.

## Users, auth and email

- Accounts live in `altcen_user` (the `User` model). Passwords are hashed with Werkzeug. Reset and confirmation tokens are signed JWTs (`models.py`) or itsdangerous tokens (`services/email.py`).
- `auth/routes.py` handles login, logout, registration, email confirmation, password reset, account deletion and OAuth (`/authorize/<provider>`, `/callback/<provider>`). Forms are in `auth/forms.py`.
- Bot protection uses Cloudflare Turnstile on the forms. Anubis at nginx guards the public list and search pages.
- Outbound mail goes through `services/email.py` (SendGrid, SES, Mailjet, and SMTP via Flask-Mail, depending on the message). The admin pages manage mass mailing, bounce and complaint webhooks (`aws_bounce`, `aws_complaint`) and email-list uploads.

## Internationalisation

- Eight languages: `en de es fr pt nl it sv`. Strings are marked with `_l()` and compiled with Babel (`alt2/translations/`).
- The navbar and some UI strings come from the `translation` table, served by `get_navtabs()`. That table's Swedish column is still named `se`, so `util.translation_column()` maps `sv` to `se`, and an old stored `se` locale is read as `sv`.

## Configuration

`config.py` reads everything from the environment. The minimum for a local run is `ALTC_DATABASE_URL`, `ALTC_SECRET_KEY`, `CACHE_REDIS_HOST` and `RANDOM_VALUE` (an anti-scraping token used in templates). Other groups of settings:

| Group | Examples |
|---|---|
| Media | `IARCHIVEURL`, `VIDEOSERVER_URL`, `AC_S3_*` |
| Image proxies | `IPROXY*`, `ACIPROXY*` |
| Cache and limits | `CACHE_REDIS_HOST` (Redis DB 1 is hardcoded) |
| Mail | `SES_*`, `SENDGRID_API_KEY`, `MJ_APIKEY_*`, `MAIL_*` |
| Auth and bot checks | `ALTC_SECRET_KEY`, `ALTC_LOGGEDIN_SECRET`, `CLOUDFLARE_*` |
| Monitoring | `SENTRY_DSN` |

`config.py` hardcodes Redis DB 1, the database production uses for its cache and rate limiter. Never run the app against production Redis or the production database from a development machine.

## Testing and checks

- `tests/` is a pytest suite that runs a real app against a seeded PostgreSQL database. It drops every table in that database, so it runs only on `www2` (`tests/run_www2.sh`). It covers public pages, auth and decorators, playlists, history, settings, admin (shell-outs recorded), sitemaps, feeds, the player, the IA lookup, cache and rate limits, error pages and translations.
- `scripts/check_ytac.sh` is the offline check. It uses a read-only database account, an in-memory cache and an unreachable Redis host. It compiles the code, scans for old-schema leftovers, loads about 20 pages through the Flask test client and checks every `Model.attribute` against the ytac models. Its baselines are in `scripts/ytac_check/`.

## Known rough edges

- The old-schema helpers in `tests/seed.py` and `tests/schema.py` are history (the old `migrations/` SQL was removed; see git history). The README still describes the pre-ytac `altcen` database and `altcen-models`.
- `EmailList` uses new column names (`subscribed`, `last_sent`, ...) while `User` keeps its `email_*` names, so code touching both must branch on the model.
- `scripts/mutation_check.py` points at the retired legacy venv.
- `alt2/templates/auth_old/` is not referenced by any Python module and looks like a leftover. Two email helpers coexist: `alt2/email.py` (used by `auth/email.py`) and `alt2/services/email.py`.
