"""Cloud poster for the DevyDose Post Desk: post the next due item in outbox/ to X.

    python poster/run_due.py --mode check        # verify the X keys (posts nothing)
    python poster/run_due.py --mode dry          # show the next due post, post nothing
    python poster/run_due.py --mode post         # post the next due post (one per run keeps the spacing)

outbox/<doc_id>/post.json is a copy of an APPROVED Post Desk doc (written by the Claude sync, which also
sets the desk doc to "queued_cloud" so the PC job never posts it too). Media paths in it are repo-relative.
A post is due when schedule_at <= now and it has no result.json. After posting, result.json records the
X ids and URL (or the failure) so it is never posted twice; the sync copies that back to the desk.
Keys come only from the X_* environment variables (GitHub Actions secrets) and are never printed.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
XPOST = os.path.join(HERE, "x_post.py")


def now():
    return datetime.now(timezone.utc)


def due_items():
    out = []
    for p in glob.glob(os.path.join(ROOT, "outbox", "*", "post.json")):
        d = os.path.dirname(p)
        if os.path.exists(os.path.join(d, "result.json")):
            continue
        doc = json.load(open(p, encoding="utf-8"))
        at = doc.get("schedule_at")
        if not at:
            continue
        when = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if when <= now():
            out.append((when, os.path.basename(d), p))
    return sorted(out)


def last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                pass
    return None


def run(args):
    r = subprocess.run([sys.executable, XPOST, *args], cwd=ROOT, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout, r.stderr


def post_one(when, doc_id, path):
    rc, so, se = run(["--file", path])
    res = last_json(so) or {"ok": False, "detail": (se or so)[-600:]}
    res.update(doc_id=doc_id, ran_at=now().strftime("%Y-%m-%dT%H:%M:%SZ"), returncode=rc)
    with open(os.path.join(os.path.dirname(path), "result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res.get(k) for k in ("doc_id", "ok", "posted_url", "failed_at", "http")}), flush=True)
    return rc


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def save(msg):
    git("add", "outbox")
    if git("diff", "--cached", "--quiet").returncode:
        git("commit", "-m", msg)
        for _ in range(3):
            if git("push", "origin", "HEAD:poster").returncode == 0:
                return
            git("pull", "--rebase", "origin", "poster")


def pending():
    out = []
    for p in glob.glob(os.path.join(ROOT, "outbox", "*", "post.json")):
        d = os.path.dirname(p)
        if not os.path.exists(os.path.join(d, "result.json")):
            doc = json.load(open(p, encoding="utf-8"))
            if doc.get("schedule_at"):
                out.append((datetime.fromisoformat(doc["schedule_at"].replace("Z", "+00:00")), os.path.basename(d), p))
    return sorted(out)


def drain(minutes):
    """Post each outbox item at its schedule_at, for up to `minutes`. Pulls the branch every loop so items
    staged after the run started are picked up; commits each result right away."""
    import time
    end = time.time() + minutes * 60
    while time.time() < end:
        git("pull", "--rebase", "-q", "origin", "poster")
        items = pending()
        due = [i for i in items if i[0] <= now()]
        if due:
            when, doc_id, path = due[0]
            post_one(when, doc_id, path)
            save(f"poster: {doc_id}")
            continue
        if not items:
            print("outbox empty", flush=True)
            time.sleep(60)
            continue
        time.sleep(max(5, min(60, (items[0][0] - now()).total_seconds())))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["check", "dry", "post"], default="post")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--drain", type=int, default=0, help="keep running up to N minutes, posting each item when due")
    a = ap.parse_args()
    if a.mode == "post" and a.drain:
        return drain(a.drain)
    if a.mode == "check":
        rc, so, se = run(["--check"])
        print(so.strip() or se.strip()[-400:])
        return rc
    items = due_items()
    print(f"{len(items)} post(s) due")
    if not items:
        return 0
    rc_all = 0
    for when, doc_id, path in items[:max(1, a.count)]:
        print(f"== {doc_id} (scheduled {when.isoformat()})")
        if a.mode == "dry":
            rc, so, se = run(["--file", path, "--dry-run"])
            print(so[-4000:], se[-800:])
            rc_all |= rc
            continue
        rc, so, se = run(["--file", path])
        res = last_json(so) or {"ok": False, "detail": (se or so)[-600:]}
        res.update(doc_id=doc_id, ran_at=now().strftime("%Y-%m-%dT%H:%M:%SZ"), returncode=rc)
        with open(os.path.join(os.path.dirname(path), "result.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
        print(json.dumps({k: res.get(k) for k in ("doc_id", "ok", "posted_url", "failed_at", "http")}))
        rc_all |= rc
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
