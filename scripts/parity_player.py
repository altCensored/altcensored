#!/usr/bin/env python3
"""Per-row playback parity between a legacy (altcen) DB and a ytac DB.

For every video in ``mv_video`` it compares the fields that
``alt2.video._resolve_video_url`` reads, and reports rows that exist on one
side only, rows whose inputs differ, and the legacy rows whose ``exists_ia``
is NULL ("unknown"), which ytac stores as False (NOT NULL).

Read-only: connections are opened read-only through libpq services, so no
credentials are handled here.

    parity_player.py OLD_SERVICE NEW_SERVICE [--samples N] [--new-table video]
    parity_player.py altc-orcl ytac-orcl
    parity_player.py altc-orcl ytac-test-orcl --new-table video

With ``--new-table video`` the new side is read from the base ``video`` table
(only for the ids in the old mv_video), so the migration's column mapping can be
checked even when the new DB's materialized views are stale or unrefreshed.
Rows that exist only in the new DB are then not reported.

Exit status 0 when every difference is a known one (NULL exists_ia -> False),
1 otherwise. Needs a python with psycopg2 (prod's venv has it).
"""
import argparse
import sys
from collections import Counter

# resolver input -> (legacy column, ytac column)
FIELDS = {
    "ac":         ("exists_ac",    "ac_exists"),
    "ia":         ("exists_ia",    "ia_exists"),
    "dark":       ("dark_ia",      "ia_dark"),
    "restricted": ("restricted_ia", "ia_restricted"),
    "loggedin":   ("loggedin_ia",  "ia_loggedin"),
    "novideo":    ("novideo_ia",   "ia_novideo"),
    "videofile":  ("videofile",    "videofile"),
    "thumbnail":  ("thumbnail",    "thumbnail_ytdlp"),
}
BOOLS = ("ac", "ia", "dark", "restricted", "loggedin", "novideo")


def normalize(row):
    """Compare booleans by truthiness (the resolver treats None like False,
    except for ``ia``, handled in classify)."""
    out = dict(row)
    for k in BOOLS:
        if k != "ia":
            out[k] = bool(row[k])
    out["videofile"] = row["videofile"] or None
    out["thumbnail"] = row["thumbnail"] or None
    return out


def classify(old, new):
    """Names of the fields that differ; 'ia-null->false' is the known one."""
    old, new = normalize(old), normalize(new)
    diffs = []
    for k in FIELDS:
        if k == "ia":
            if old["ia"] is None and new["ia"] is False:
                diffs.append("ia-null->false")
            elif bool(old["ia"]) != bool(new["ia"]):
                diffs.append("ia")
        elif old[k] != new[k]:
            diffs.append(k)
    return diffs


def compare(old_rows, new_rows):
    """Both args map extractor_data -> row dict (keys of FIELDS)."""
    only_old = sorted(old_rows.keys() - new_rows.keys())
    only_new = sorted(new_rows.keys() - old_rows.keys())
    by_diff = {}
    for vid in old_rows.keys() & new_rows.keys():
        d = classify(old_rows[vid], new_rows[vid])
        if d:
            by_diff.setdefault(tuple(d), []).append(vid)
    return only_old, only_new, {k: sorted(v) for k, v in by_diff.items()}


def fetch(service, side, table="mv_video", ids=None):
    import psycopg2
    conn = psycopg2.connect(service=service)
    conn.set_session(readonly=True)
    idx = 0 if side == "old" else 1
    cols = ", ".join(f"{c[idx]} AS {k}" for k, c in FIELDS.items())
    keys = list(FIELDS)
    rows = {}
    if ids is None:
        cur = conn.cursor(name="parity")
        cur.itersize = 20000
        cur.execute(f"SELECT extractor_data, {cols} FROM {table}")
        rows = {r[0]: dict(zip(keys, r[1:])) for r in cur}
    else:
        ids = sorted(ids)
        for i in range(0, len(ids), 50000):
            cur = conn.cursor()
            cur.execute(f"SELECT extractor_data, {cols} FROM {table} "
                        "WHERE extractor_data = ANY(%s)", (ids[i:i + 50000],))
            rows.update({r[0]: dict(zip(keys, r[1:])) for r in cur})
    conn.close()
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old_service")
    ap.add_argument("new_service")
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--new-table", choices=("mv_video", "video"),
                    default="mv_video")
    a = ap.parse_args(argv)

    old = fetch(a.old_service, "old")
    if a.new_table == "video":
        new = fetch(a.new_service, "new", "video", ids=old.keys())
    else:
        new = fetch(a.new_service, "new")
    only_old, only_new, by_diff = compare(old, new)
    if a.new_table == "video":
        only_new = []   # every video is in the base table; not meaningful
    print(f"mv_video rows: old={len(old)} new={len(new)} "
          f"common={len(old.keys() & new.keys())}")
    print(f"only in old: {len(only_old)}   only in new: {len(only_new)}"
          + ("   (new read from base table)" if a.new_table == "video" else ""))
    for label, ids in (("old", only_old), ("new", only_new)):
        if ids:
            print(f"  e.g. only in {label}: {', '.join(ids[:a.samples])}")

    unexpected = 0
    print("\ndifferences in resolver inputs (common rows):")
    if not by_diff:
        print("  none")
    for diff, ids in sorted(by_diff.items(), key=lambda kv: -len(kv[1])):
        known = diff == ("ia-null->false",)
        unexpected += 0 if known else len(ids)
        print(f"  {'known     ' if known else 'UNEXPECTED'} {'+'.join(diff):28} "
              f"{len(ids):>8}   e.g. {', '.join(ids[:a.samples])}")

    nulls = sorted(v for v, r in old.items() if r["ia"] is None)
    print(f"\nlegacy rows with exists_ia NULL: {len(nulls)}")
    for vid in nulls:
        r = old[vid]
        n = new.get(vid)
        flags = [k for k in ("dark", "restricted", "loggedin", "novideo") if r[k]]
        # what the resolver does if the S3 object is missing, ignoring the network
        if flags:
            after = "unavailable (IA restriction flag)"
        elif r["videofile"] or (r["thumbnail"] and "maxresdefault" not in r["thumbnail"]
                                and not r["thumbnail"].startswith(("http://", "https://"))):
            after = "IA download URL"
        else:
            after = "IA lookup before; unavailable after (ia_exists False)"
        print(f"  {vid}  ac={r['ac']} flags={flags or '-'}  "
              f"new={'missing from new mv_video' if n is None else 'ia=' + str(n['ia'])}"
              f"  if S3 object missing: {after}")

    print(f"\nunexpected differences: {unexpected + len(only_old) + len(only_new)}"
          f" (rows on one side only count too)")
    return 0 if unexpected == 0 and not only_old and not only_new else 1


if __name__ == "__main__":
    sys.exit(main())
