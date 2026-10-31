#!/usr/bin/env python3
"""Row-by-row parity of the channel, category, playlist and user materialized
views between a legacy (altcen) DB and a ytac DB.

parity_player.py covers mv_video; this covers the other four views that the
pages read. Each view has a key and a field mapping (legacy column, ytac column).
Differences are sorted into:

  UNEXPECTED  a field that should match does not
  drift       a counter (views, subscribers, ...) that moves between snapshots;
              reported, never fails the run
  only-old / only-new  keys present on one side only (a stale snapshot shows up here)

Read-only: connections are opened read-only through libpq services.

    parity_views.py OLD_SERVICE NEW_SERVICE [--view mv_channel ...] [--samples N]
    parity_views.py altc-orcl ytac-orcl

Exit status 0 when there are no UNEXPECTED differences and no one-sided keys.
Needs a python with psycopg2 (prod's venv has it).
"""
import argparse
import sys

# view -> (key (legacy, ytac), {name: (legacy column, ytac column, volatile)})
SPEC = {
    "mv_channel": (("ytc_id", "extractor_data"), {
        "title":         ("ytc_title", "title", False),
        "deleted":       ("ytc_deleted", "deleted", False),
        "archive":       ("ytc_archive", "archive_full", False),
        "partarchive":   ("ytc_partarchive", "archive_part", False),
        "latestarchive": ("ytc_latestarchive", "archive_latest", False),
        "delta":         ("delta", "delta", False),
        "allow":         ("allow", "allow", False),
        "total":         ("total", "total", True),
        "limited":       ("limited", "limited", True),
        "archived":      ("archived", "archived", True),
        "views":         ("ytc_viewcount", "view_count", True),
        "subscribers":   ("ytc_subscribercount", "channel_follower_count", True),
    }),
    "mv_category": (("cat_name", "name"), {
        "id":    ("cat_id", "id", False),
        "image": ("cat_image", "icon", False),
        "count": ("cat_count", "video_count", True),
    }),
    "mv_playlist": (("hashid", "hashid"), {
        "title":       ("title", "title", False),
        "user_id":     ("user_id", "user_id", False),
        "public":      ("public", "public", False),
        "videos":      ("videos", "videos", False),
        "video_count": ("video_count", "video_count", False),
        "featured":    ("featured_video_id", "featured_video_id", False),
        "views":       ("view_counter", "view_counter", True),
    }),
    "mv_altcen_user": (("username", "username"), {
        "id":          ("id", "id", False),
        "description": ("description", "description", False),
        "public":      ("public", "public", False),
        "views":       ("view_counter", "view_counter", True),
    }),
}


def norm(value):
    """None and '' are the same; arrays compare as lists."""
    if value == "":
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return value


def classify(view, old, new):
    """(unexpected, drift): names of the fields that differ."""
    unexpected, drift = [], []
    for name, (_, _, volatile) in SPEC[view][1].items():
        if norm(old[name]) != norm(new[name]):
            (drift if volatile else unexpected).append(name)
    return unexpected, drift


def compare(view, old_rows, new_rows):
    """Both args map key -> {field: value}. Returns
    (only_old, only_new, unexpected {field: [keys]}, drift {field: [keys]})."""
    only_old = sorted(old_rows.keys() - new_rows.keys())
    only_new = sorted(new_rows.keys() - old_rows.keys())
    unexpected, drift = {}, {}
    for key in old_rows.keys() & new_rows.keys():
        u, d = classify(view, old_rows[key], new_rows[key])
        for f in u:
            unexpected.setdefault(f, []).append(key)
        for f in d:
            drift.setdefault(f, []).append(key)
    return (only_old, only_new,
            {f: sorted(k) for f, k in unexpected.items()},
            {f: sorted(k) for f, k in drift.items()})


def fetch(service, side, view):
    import psycopg2
    idx = 0 if side == "old" else 1
    key_col = SPEC[view][0][idx]
    fields = SPEC[view][1]
    cols = ", ".join(f"{spec[idx]} AS {name}" for name, spec in fields.items())
    conn = psycopg2.connect(service=service)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute(f"SELECT {key_col}, {cols} FROM {view}")
    names = list(fields)
    rows = {r[0]: dict(zip(names, r[1:])) for r in cur}
    conn.close()
    return rows


def report(view, old, new, samples):
    only_old, only_new, unexpected, drift = compare(view, old, new)
    print(f"\n== {view}: old={len(old)} new={len(new)} "
          f"common={len(old.keys() & new.keys())}")
    print(f"   only in old: {len(only_old)}   only in new: {len(only_new)}")
    for label, keys in (("old", only_old), ("new", only_new)):
        if keys:
            print(f"     e.g. only in {label}: "
                  f"{', '.join(str(k) for k in keys[:samples])}")
    for f, keys in sorted(unexpected.items(), key=lambda kv: -len(kv[1])):
        print(f"   UNEXPECTED {f:14} {len(keys):>7}   e.g. "
              f"{', '.join(str(k) for k in keys[:samples])}")
    for f, keys in sorted(drift.items(), key=lambda kv: -len(kv[1])):
        print(f"   drift      {f:14} {len(keys):>7}")
    if not unexpected and not drift:
        print("   fields: identical")
    return sum(map(len, unexpected.values())) + len(only_old) + len(only_new)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old_service")
    ap.add_argument("new_service")
    ap.add_argument("--view", action="append", choices=sorted(SPEC),
                    help="limit to a view (repeatable); default all four")
    ap.add_argument("--samples", type=int, default=5)
    a = ap.parse_args(argv)

    problems = 0
    for view in a.view or sorted(SPEC):
        problems += report(view, fetch(a.old_service, "old", view),
                           fetch(a.new_service, "new", view), a.samples)
    print(f"\nunexpected differences + one-sided keys: {problems}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
