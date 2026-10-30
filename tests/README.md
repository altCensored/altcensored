# Tests

Real app, real PostgreSQL, small seeded dataset (`seed.py`). Needs a dedicated
database whose name ends in `_test`; the suite drops and recreates everything in it.

    ALTC_TEST_DATABASE_URL='postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw' \
      venv/bin/python -m pytest tests

On www2 the service entry avoids handling a password. Never point this at www or orcl.
`fixtures/` holds UI text and the materialized-view DDL exported from prod; re-export
`matviews.sql` when a migration changes a view.
