#!/bin/bash
# Run the test suite from this clone against the shared test database on www2.
# Usage: tests/run.sh [pytest args...]
# Needs `venv/` (pip install -r requirements.txt -r requirements-test.txt, plus the ytac package)
# and the libpq service `ytactestac-www2` in ~/.pg_service.conf / ~/.pgpass. The suite drops and
# recreates every table in that database, so it is the only database this script will use.
# Nothing is copied to www2, and no credentials live there.
set -eu
cd "$(dirname "$0")/.."
export ALTC_TEST_DATABASE_URL='postgresql+psycopg2:///ytac_test_ac?service=ytactestac-www2'
echo "=== local $(git rev-parse --short HEAD)$(git diff --quiet HEAD -- alt2 tests || echo ' + uncommitted changes')"
exec venv/bin/python -m pytest -q "$@"
