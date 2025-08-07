# altCensored

Flask and Postgresql based altcensored.com website.

Production runs behind an nginx server with the included gunicorn as the Flask app server, without Docker.


System Requirements:
- local or remote Postgresql database 'altcen'. see al2/models for database layouts.
- redis server installed with defaults


altcen_sample_database_pg_dump.sql is included for testing. Prospective developers can contact us for access to this sample database on a public test server.

admin @ altcensored .com | altcensored @ protonmail .com