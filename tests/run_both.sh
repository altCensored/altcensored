#!/bin/bash
# Sync tests/ to www2 and run them on both stacks (legacy, then ytac-cutover).
# Usage: tests/run_both.sh [pytest args...]
# A failure on one stack only is a cutover regression. Never run on prod hosts.
set -u
cd "$(dirname "$0")/.."
HOST=lc@100.64.0.10   # www2 tailnet IP (www cannot use MagicDNS)
URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw'
rc=0
for d in altcensored-master altcensored; do
  rsync -a --delete --exclude __pycache__ tests/ "$HOST:/opt/altcen/$d/tests/"
  rsync -a pytest.ini "$HOST:/opt/altcen/$d/"
  extra=""
  # the cutover branch lacks scripts/parity_player.py until master is merged in
  [ "$d" = altcensored ] && ssh "$HOST" "test -f /opt/altcen/$d/scripts/parity_player.py" \
    || { [ "$d" = altcensored ] && extra="--ignore=tests/test_parity_player.py"; }
  echo "=== $d"
  ssh "$HOST" "cd /opt/altcen/$d && ALTC_TEST_DATABASE_URL='$URL' venv/bin/python -m pytest -q $extra $* 2>&1 | tail -60" || rc=1
done
exit $rc
