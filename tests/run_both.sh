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
  # the parity scripts are tested too; the cutover checkout only gets them this way
  # until master is merged into it (no --delete: its own scripts/ stays untouched)
  ssh "$HOST" "mkdir -p /opt/altcen/$d/scripts"
  rsync -a scripts/parity_*.py "$HOST:/opt/altcen/$d/scripts/"
  echo "=== $d"
  ssh "$HOST" "cd /opt/altcen/$d && ALTC_TEST_DATABASE_URL='$URL' venv/bin/python -m pytest -q $* 2>&1 | tail -60" || rc=1
done
exit $rc
