# CLAUDE.md

After pushing to `origin` (GitHub), also push to `codeberg` and `bbucket_key` (Bitbucket).

## Deploying

- the app runs from `/opt/altcen/altcensored` (branch `master`), served by `gunicorn.service` as root.
- The checkout is root-owned, so use `sudo git` there (plain `git` as `lc` fails with "dubious ownership").
- Update: `ssh lc@100.64.0.2` (not needed when already on www, which is that node), then in the checkout `sudo git fetch origin master && sudo git merge --ff-only FETCH_HEAD`, then `sudo systemctl reload gunicorn` (graceful SIGHUP).
- When ytac changes the schema, upgrade ytac in `/opt/altcen/altcensored/venv` in the same step (check `sudo venv/bin/pip show ytac`), or pages 500: the app's models come from that package.
- Verify through the socket, since the public host answers curl with an Anubis 307: `curl --unix-socket /run/gunicorn.sock -H 'Host: altcensored.com' -H 'X-Forwarded-Proto: https' http://localhost/<path>`.

