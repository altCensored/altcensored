#!/bin/bash
# Run the test suite on www2 (the test node). Never run on prod hosts.
# Usage: [BRANCH=<name>] tests/run_www2.sh [--local] [pytest args...]
#   default  fetch and check out BRANCH (default master) in the www2 checkout, fast-forward only,
#            so a run tests one pushed commit (the hash is printed). Push the branch first.
#   --local  test what is in THIS clone, uncommitted tests included: tests/, pytest.ini and
#            scripts/parity_*.py are rsynced over the www2 checkout, and afterwards the
#            checkout is restored to its commit. It cannot test changes under alt2/.
set -u
cd "$(dirname "$0")/.."
LOCAL=0
if [ "${1:-}" = "--local" ]; then LOCAL=1; shift; fi
BRANCH="${BRANCH:-master}"
HOST=lc@100.64.0.10   # www2 tailnet IP (www cannot use MagicDNS)
URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw'
dir=/opt/altcen/altcensored
echo "=== www2 $dir ($BRANCH)"
if ! ssh "$HOST" "cd $dir && [ -z \"\$(git status --porcelain)\" ]"; then
  echo "  www2 checkout $dir is not clean; fix it before running" >&2; exit 1
fi
if [ $LOCAL = 1 ]; then
  rsync -a --delete --exclude __pycache__ tests/ "$HOST:$dir/tests/"
  rsync -a pytest.ini "$HOST:$dir/"
  rsync -a scripts/parity_*.py "$HOST:$dir/scripts/"
  echo "  local files (not a pushed commit); checkout is at: $(ssh "$HOST" "cd $dir && git rev-parse --short HEAD")"
else
  ssh "$HOST" "cd $dir && git fetch -q origin $BRANCH && git checkout -q -B $BRANCH FETCH_HEAD" || exit 1
  echo "  commit: $(ssh "$HOST" "cd $dir && git log --oneline -1")"
fi
rc=0
ssh "$HOST" "cd $dir && ALTC_TEST_DATABASE_URL='$URL' venv/bin/python -m pytest -q $* 2>&1 | tail -60" || rc=1
if [ $LOCAL = 1 ]; then
  # put the checkout back: tracked files restored, files only in the local copy removed
  ssh "$HOST" "cd $dir && git checkout -q -- tests pytest.ini scripts && git clean -fdq tests"
fi
exit $rc
