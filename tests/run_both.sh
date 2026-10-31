#!/bin/bash
# Run the suite on www2 against both stacks (legacy master, then ytac-cutover).
# Usage: tests/run_both.sh [--local] [pytest args...]
#   default  git pull --ff-only in each www2 checkout, so a run tests one pushed commit
#            per stack (the hash is printed).
#   --local  test what is in THIS clone, uncommitted work included: tests/, pytest.ini and
#            scripts/parity_*.py are rsynced over the www2 checkouts, and afterwards the
#            checkouts are restored to their commit. Use it before pushing.
# A failure on one stack only is a cutover regression. Never run on prod hosts.
set -u
cd "$(dirname "$0")/.."
LOCAL=0
if [ "${1:-}" = "--local" ]; then LOCAL=1; shift; fi
HOST=lc@100.64.0.10   # www2 tailnet IP (www cannot use MagicDNS)
URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw'
rc=0
# directory on www2 : branch it tracks
for pair in altcensored-master:master altcensored:ytac-cutover; do
  d=${pair%%:*}; branch=${pair##*:}; dir=/opt/altcen/$d
  echo "=== $d ($branch)"
  if ! ssh "$HOST" "cd $dir && [ -z \"\$(git status --porcelain)\" ]"; then
    echo "  www2 checkout $dir is not clean; fix it before running" >&2; rc=1; continue
  fi
  if [ $LOCAL = 1 ]; then
    rsync -a --delete --exclude __pycache__ tests/ "$HOST:$dir/tests/"
    rsync -a pytest.ini "$HOST:$dir/"
    rsync -a scripts/parity_*.py "$HOST:$dir/scripts/"
    echo "  local files (not a pushed commit); checkout is at: $(ssh "$HOST" "cd $dir && git rev-parse --short HEAD")"
  else
    ssh "$HOST" "cd $dir && git pull -q --ff-only origin $branch" || { rc=1; continue; }
    echo "  commit: $(ssh "$HOST" "cd $dir && git log --oneline -1")"
  fi
  ssh "$HOST" "cd $dir && ALTC_TEST_DATABASE_URL='$URL' venv/bin/python -m pytest -q $* 2>&1 | tail -60" || rc=1
  if [ $LOCAL = 1 ]; then
    # put the checkout back: tracked files restored, files only in the local copy removed
    ssh "$HOST" "cd $dir && git checkout -q -- tests pytest.ini scripts && git clean -fdq tests"
  fi
done
exit $rc
