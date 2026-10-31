#!/bin/bash
# Check the ytac-cutover worktree after a master merge: static leftovers + test-client smoke run.
# Read-only: DB is orcl ytac as claude_ro (or $YTAC_CHECK_SERVICE), cache/limiter are in-memory, Redis host is unreachable.
set -uo pipefail
cd "$(dirname "$0")/.."
# The libpq service the smoke run reads (read-only claude_ro). Default: orcl's ytac DB. For the
# www2 rehearsal (R9) use the rehearsal copy: YTAC_CHECK_SERVICE=ytac-www2 scripts/check_ytac.sh
SERVICE="${YTAC_CHECK_SERVICE:-ytac-orcl}"
echo "== database service: $SERVICE"
fail=0

echo "== compile"
.venv/bin/python -m compileall -q alt2 || fail=1

echo "== conflict markers"
if grep -rnE '^(<<<<<<<|=======$|>>>>>>>)' alt2/; then fail=1; fi

echo "== altcen-models / flask-login leftovers (new ones only; known ones in scripts/ytac_check/leftovers_baseline.txt)"
leftovers() {
    grep -rnE "\.ytc_[a-z]|\['ytc_[a-z]|\bEntity\b|altcen_models|flask_login|\blogin_user\(|\blogout_user\(|\bcurrent_user\b" \
        --include=*.py --include=*.html --include=*.xml alt2/ | sed -E 's/^([^:]*):[0-9]+:[[:space:]]*/\1: /' | sort -u
}
if [ "${1:-}" = "--rebaseline" ]; then leftovers > scripts/ytac_check/leftovers_baseline.txt; fi
new=$(comm -13 scripts/ytac_check/leftovers_baseline.txt <(leftovers))
if [ -n "$new" ]; then echo "$new"; fail=1; fi
echo "  known leftovers: $(wc -l < scripts/ytac_check/leftovers_baseline.txt)"

echo "== test client"
ALTC_DATABASE_URL="postgresql+psycopg2:///ytac?service=$SERVICE" \
ALTC_SECRET_KEY=check ALTC_LOGGEDIN_SECRET=check RANDOM_VALUE=check \
CACHE_REDIS_HOST=127.0.0.2 \
.venv/bin/python -I - <<'EOF' || fail=1
import sys, os
sys.path.insert(0, os.getcwd())
from alt2 import create_app, util
from alt2.cache import cache
from alt2.database import db_session
from alt2.models import MvVideo, MvChannel

app = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False, 'RATELIMIT_STORAGE_URI': 'memory://'})
cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})
backend = type(app.extensions['cache'][cache]).__name__
if backend != 'SimpleCache':
    sys.exit(f"refusing to run: cache backend is {backend}, not SimpleCache")

v = db_session.query(MvVideo).first()
c = db_session.query(MvChannel).first()
pages = ['/', '/channel', '/channel/deleted', '/channel/deleted/feed', '/sitemap.xml', '/feed',
         '/auth/login', '/auth/logout', '/search?q=test', '/playlist/']
if v is not None:
    pages.append(f"/watch?v={getattr(v, 'extractor_data', None) or getattr(v, 'id')}")
if c is not None:
    pages.append(f"/channel/{getattr(c, 'extractor_data', None) or getattr(c, 'id')}")

known = {l.split('#')[0].strip() for l in open('scripts/ytac_check/known_bad_pages.txt') if l.split('#')[0].strip()}
bad = 0
client = app.test_client()
for p in pages:
    try:
        r = client.get(p, base_url='https://localhost')
        status = r.status_code
    except Exception as e:
        status = f'EXC {type(e).__name__}: {e}'
    ok = isinstance(status, int) and status < 500
    if p in known:
        print(f"  {'FIXED? (remove from known_bad_pages.txt)' if ok else 'known'} {status} {p}")
        continue
    bad += not ok
    print(f"  {'ok ' if ok else 'BAD'} {status} {p}")

if not hasattr(util, 'make_loggedin_cookie'):
    print("  --  signed loggedin cookie: helper not on this branch yet")
    sys.exit(1 if bad else 0)
with app.test_request_context():
    val = util.make_loggedin_cookie()
    if not util.loggedin_cookie_valid(val):
        print("  BAD signed loggedin cookie round-trip"); bad += 1
    else:
        print("  ok  signed loggedin cookie round-trip")
sys.exit(1 if bad else 0)
EOF

echo "== Model.attribute references exist on the ytac models"
ALTC_DATABASE_URL="postgresql+psycopg2:///ytac?service=$SERVICE" CACHE_REDIS_HOST=127.0.0.2 \
.venv/bin/python -I - <<'EOF' || fail=1
import sys, os, re, glob
sys.path.insert(0, os.getcwd())
import alt2.models as m
names = [n for n in dir(m) if isinstance(getattr(m, n), type) and hasattr(getattr(m, n), '__mapper__')]
pat = re.compile(r'\b(' + '|'.join(names) + r')\.(\w+)')
bad = 0
for f in sorted(glob.glob('alt2/**/*.py', recursive=True)):
    for i, line in enumerate(open(f), 1):
        if line.lstrip().startswith('#'):
            continue
        for cls, attr in pat.findall(line):
            if not hasattr(getattr(m, cls), attr):
                print(f"  BAD {f}:{i} {cls}.{attr}"); bad += 1
print(f"  {'ok ' if not bad else 'BAD'} {len(names)} models checked")
sys.exit(1 if bad else 0)
EOF

echo "== email helpers set real columns (EmailList renamed email_*; AltcenUser didn't)"
ALTC_DATABASE_URL="postgresql+psycopg2:///ytac?service=$SERVICE" \
ALTC_SECRET_KEY=check ALTC_LOGGEDIN_SECRET=check RANDOM_VALUE=check \
CACHE_REDIS_HOST=127.0.0.2 \
.venv/bin/python -I - <<'EOF' || fail=1
import sys, os
from unittest import mock
sys.path.insert(0, os.getcwd())
from sqlalchemy import inspect
from alt2 import admin
from alt2.models import EmailList, User

def stray(obj):
    # attributes set on the object that aren't mapped: they are never saved
    mapped = set(inspect(type(obj)).attrs.keys())
    return sorted(k for k in vars(obj) if not k.startswith('_') and k not in mapped)

def fake_session(row, added):
    s = mock.MagicMock()
    s.query.return_value.filter.return_value.one.return_value = row
    s.query.return_value.filter.return_value.one_or_none.return_value = row
    s.add.side_effect = added.append
    return s

bad = 0
def report(name, obj, expect):
    global bad
    problems = stray(obj) + [f"{k}={getattr(obj, k, None)!r} (want {v!r})" for k, v in expect.items()
                             if v is not ... and getattr(obj, k, None) != v]
    bad += bool(problems)
    print(f"  {'BAD' if problems else 'ok '} {name}" + (f": {problems}" if problems else ""))

for model, is_user in ((EmailList, False), (User, True)):
    row = model(email='x@example.org')
    added = []
    with mock.patch.object(admin, 'db_session', fake_session(row, added)):
        admin.db_unsubscribe_email('User' if is_user else 'EmailList', 'x@example.org', 'check')
    if is_user:
        report("unsubscribe User", row, {'email_subscribed': False, 'email_action': 'check'})
    else:
        report("unsubscribe EmailList", row, {'subscribed': False, 'action': 'check'})

    row = model(email='x@example.org')
    with mock.patch.object(admin, 'db_session', fake_session(row, [])), \
         mock.patch.object(admin, 'email_exists', return_value=is_user), \
         mock.patch.object(admin, 'Thread'), mock.patch.object(admin, 'render_template', return_value=''), \
         mock.patch.object(admin, 'url_for', return_value='u'), \
         mock.patch.object(admin, 'generate_confirmation_token', return_value='t'):
        admin.send_mass_email('x@example.org', 's', 'subj', 'f.html', 'svc')
    field = 'email_lastsent_date' if is_user else 'last_sent'
    report(f"sent marker {model.__name__}", row, {})
    if getattr(row, field, None) is None:
        print(f"  BAD sent marker {model.__name__}: {field} not set"); bad += 1

added = []
with mock.patch.object(admin, 'db_session', fake_session(None, added)):
    try:
        admin.db_add_email_list('New@Example.org', 'check')
    except TypeError as e:
        print(f"  BAD add to email list: {e}"); bad += 1
if added:
    report("add to email list", added[0], {'email': 'new@example.org', 'source': 'check'})
sys.exit(1 if bad else 0)
EOF

echo "== result: $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
