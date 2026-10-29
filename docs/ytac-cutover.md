# `ytac-cutover` branch

A long-lived branch, on all three remotes, that moves the app from `altcen-models` to the private `ytac` package. The new schema renames columns: `ytc_deleted` → `deleted`, `ytc_deleteddate` → `deleted_date`, `ytc_subscribercount` → `channel_follower_count`, `ytc_id` → `extractor_data`, and so on. There is no `Entity`, `User` is `AltcenUser`, and flask-login is removed. Keep it current with master:

- **After every master deploy**, merge master into it in the worktree `~/src/altcensored-ytac`: `git merge master`. Always merge, never rebase or force-push. `rerere` is enabled, so resolved conflicts are reapplied.
- A change that merges cleanly can still be wrong there. Translate any new `ytc_*` column access, `Entity` use or flask-login call to the ytac names.
- Run `~/src/altcensored-ytac/scripts/check_ytac.sh`. It must say PASS. It compiles the code, flags new altcen-models leftovers and conflict markers, and runs the test client against orcl's `ytac` DB as read-only `claude_ro`, with an in-memory cache, so prod Redis and data are untouched. Known pre-existing failures are listed in `scripts/ytac_check/known_bad_pages.txt` and `scripts/ytac_check/leftovers_baseline.txt` there.
- Commit the merge and push the branch to all three remotes. Never merge it into master or deploy it as part of a sync; the cutover is its own decision.

**Scope:** work in this repo covers altcensored branches only (`master`, `ytac-cutover`, and working branches off them). The `ytac` and `ytac-archive` repos are handled by a separate Claude session, so don't change them from here. Reading ytac files (below) is fine.

**ytac version:** `ytac-cutover`'s `requirements.txt` pins ytac to a git tag; read the current pin with `git show ytac-cutover:requirements.txt | grep ytac` rather than trusting any copy here. ytac uses date versions (`YYYY.M.D.N`) and auto-tags every push, so a newer tag is **not** a reason to upgrade. Move the pin only when the ytac session asks for it in its handover reply (`~/src/ytac/.claude/HANDOVER-altcensored.md`) and the user agrees. Do it on a working branch: change the pin, `pip install -U` in `~/src/altcensored-ytac/.venv`, and run the check script.

References in the private `altCensored/ytac` repo. Read them with `gh api repos/altCensored/ytac/contents/<path> -H 'Accept: application/vnd.github.raw'`; links won't work for public readers.
- `YTAC_CUTOVER.md` has the old → new column mapping for every materialized view, plus the `email_list` renames. `EmailList` uses `subscribed`, `last_sent`, `source`, `action` and `created`, while `AltcenUser` keeps its `email_*` names, so code that touches both must branch on the model. ytac itself provides `MvPlaylist.user` and the materialized-view write guard; don't re-add them in `alt2/models.py`.
- ytac's own `tests/` suite covers the ytac package, not this app's pages. See "Testing" in `CLAUDE.md` for the integration-test warning.
