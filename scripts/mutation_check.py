#!/usr/bin/env python3
"""Mutation check: break the app on purpose and see whether the test suite notices.

Each mutation is one exact-text replacement in a source file. For every one, this
copies alt2/, tests/, scripts/ and pytest.ini to a throwaway directory on www2
(~/mut/m<N>), applies the replacement there, runs the whole suite with -x on the
legacy stack, and deletes the directory. Neither this clone nor the www2 checkouts
are touched. The suite drops every table in the www2 test database, so never run two
at once (including run_both.sh).

  CAUGHT   a test failed: the suite guards this behaviour.
  MISSED   the whole suite passed with the code broken: a gap, add a test.
  SKIPPED  the text to replace is not (or no longer) in the file once: update MUTATIONS.
  UNKNOWN  no pytest result came back (ssh or pytest crashed).

Usage (from this clone, any time after a large change to one of these areas):
  scripts/mutation_check.py --list
  scripts/mutation_check.py              # all mutations, about 30-100 s each
  scripts/mutation_check.py 0 5 12       # by number
  scripts/mutation_check.py --baseline   # unchanged tree must pass, or the harness is off
Exit status is 0 only if every mutation run was CAUGHT.

Only the legacy (master) code is mutated: the same alt2/ text exists on ytac-cutover
apart from the ytac renames, and the suite is checked there by tests/run_both.sh.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "lc@100.64.0.10"   # www2 (test node), tailnet IP: www cannot use MagicDNS
URL = "postgresql+psycopg2://@/altcen_test?service=altc-www2-test-rw"
PYTHON = "/opt/altcen/altcensored-master/venv/bin/python"   # legacy stack's interpreter

# (name, file, text to find (must occur exactly once), replacement)
MUTATIONS = [
    ("admin gate off", "alt2/util.py",
     "if session.get('user') is None or session['user']['username'] != 'admin':", "if False:"),
    ("admin gate: any user", "alt2/util.py",
     "if session.get('user') is None or session['user']['username'] != 'admin':",
     "if session.get('user') is None:"),
    ("login_required off", "alt2/util.py",
     "        if session.get('user') is None:\n            return redirect(url_for('video.index'))\n"
     "        return view(**kwargs)\n    return wrapped_view\n\n\ndef admin_login_required",
     "        return view(**kwargs)\n    return wrapped_view\n\n\ndef admin_login_required"),
    ("cookie signature ignored", "alt2/util.py",
     "if not hmac.compare_digest(sig, _loggedin_sig(expires)):", "if False:"),
    ("cookie expiry ignored", "alt2/util.py",
     "return int(expires) > time.time() + min_remaining", "return True"),
    ("safe_next any host", "alt2/util.py",
     "        if parts.netloc.lower() not in hosts:\n            return default\n", "        pass\n"),
    ("safe_next allows //", "alt2/util.py",
     "or path.startswith('//') or '\\\\' in path", "or '\\\\' in path"),
    ("list cap removed", "alt2/util.py",
     "func.cardinality(arr) < MAX_LIST_VIDEOS)", "func.cardinality(arr) < MAX_LIST_VIDEOS + 10**6)"),
    ("list duplicates allowed", "alt2/util.py",
     "               not_(literal(v) == any_(arr)),\n", ""),
    ("sv not mapped to se", "alt2/util.py",
     "config.TRANSLATION_COLUMNS.get(locale, locale)", "locale"),
    ("valid_video_id always true", "alt2/util.py",
     "return isinstance(v, str) and VIDEO_ID_RE.match(v) is not None", "return True"),
    ("cookie refresh: feeds not skipped", "alt2/__init__.py",
     "                and not request.path.startswith(LOGGEDIN_NO_REFRESH)\n", ""),
    ("cookie refresh: any mimetype", "alt2/__init__.py",
     "                and response.mimetype == 'text/html'\n", ""),
    ("history ignores page offset", "alt2/user.py",
     "order_by(ordering).limit(PER_PAGE).offset(offset)\n    videocount = len(user.watched)",
     "order_by(ordering).limit(PER_PAGE).offset(0)\n    videocount = len(user.watched)"),
    ("search ignores page offset", "alt2/video.py",
     "order_by(video_order) \\\n        .limit(PER_PAGE).offset(offset)",
     "order_by(video_order) \\\n        .limit(PER_PAGE).offset(0)"),
    ("register ignores turnstile result", "alt2/auth/routes.py",
     "        if verification_result.get('success'):\n            create_user_altcen(user)",
     "        if True:\n            create_user_altcen(user)"),
    ("register skips welcome mail", "alt2/auth/routes.py",
     "            create_user_altcen(user)\n            send_welcome_email(user)\n            conf_email_sent",
     "            create_user_altcen(user)\n            conf_email_sent"),
]


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, **kw)


def check(label, rel_file, replacement_text):
    """Run the suite on www2 with rel_file replaced by replacement_text (None = unchanged)."""
    tag = "base" if replacement_text is None else label.split("]")[0].lstrip("[")
    d = f"mut/m{tag}"
    run(["ssh", HOST, f"rm -rf ~/{d} && mkdir -p ~/{d}"], check=True)
    try:
        run(["rsync", "-a", "--exclude", "__pycache__", f"{ROOT}/alt2", f"{ROOT}/tests",
             f"{ROOT}/pytest.ini", f"{ROOT}/scripts", f"{HOST}:{d}/"], check=True)
        if replacement_text is not None:
            with tempfile.NamedTemporaryFile("w", suffix=".py") as tmp:
                tmp.write(replacement_text)
                tmp.flush()
                run(["scp", "-q", tmp.name, f"{HOST}:{d}/{rel_file}"], check=True)
        r = run(["ssh", HOST,
                 f"cd ~/{d} && ALTC_TEST_DATABASE_URL='{URL}' {PYTHON} -m pytest -x -q "
                 "-p no:cacheprovider 2>&1 | grep -E '^(FAILED|ERROR)|passed|failed|error' | head -4"],
                capture_output=True)
    finally:
        run(["ssh", HOST, f"rm -rf ~/{d}"])
    out = r.stdout.strip().replace("\n", " | ")
    if "FAILED" in out or "ERROR" in out or " failed" in out:
        return "CAUGHT", out
    if " passed" in out:
        return "MISSED", out
    return "UNKNOWN", out or "(no output)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("numbers", nargs="*", type=int, help="mutation numbers (default: all)")
    ap.add_argument("--list", action="store_true", help="list the mutations and exit")
    ap.add_argument("--baseline", action="store_true",
                    help="run the unchanged tree once: it must pass")
    args = ap.parse_args()

    if args.list:
        for i, (name, f, _, _) in enumerate(MUTATIONS):
            print(f"[{i}] {name}  ({f})")
        return 0

    if args.baseline:
        verdict, out = check("baseline", None, None)
        ok = verdict == "MISSED"   # "nothing failed" is the good outcome here
        print(f"baseline: {'PASS' if ok else 'PROBLEM'}: {out}")
        return 0 if ok else 1

    bad = 0
    for i, (name, rel_file, old, new) in enumerate(MUTATIONS):
        if args.numbers and i not in args.numbers:
            continue
        text = (ROOT / rel_file).read_text()
        if text.count(old) != 1:
            print(f"[{i}] {name}: SKIPPED, text found {text.count(old)} times in {rel_file}", flush=True)
            bad += 1
            continue
        verdict, out = check(f"[{i}]", rel_file, text.replace(old, new))
        print(f"[{i}] {name}: {verdict}: {out[:200]}", flush=True)
        bad += verdict != "CAUGHT"
    print(f"\n{'all caught' if not bad else str(bad) + ' not caught (MISSED, SKIPPED or UNKNOWN)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
