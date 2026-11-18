"""Stage approved Post Desk docs into outbox/ (used by the hourly Claude sync).

    python poster/stage.py <desk_json_dir> <image_dir>

<desk_json_dir>: Post Desk `posts` docs saved by ArtifactData (out_dir), one <doc_id>.json each (the doc's data).
<image_dir>: images downloaded from the Post Desk asset store, named <asset_id>.<ext> (Artifact read, path = id).
A doc is staged when status is "approved", it has schedule_at, it is not already in outbox/, and every image
in its media_urls is present. Its schedule_at is kept as-is. Prints the staged doc ids as JSON (the caller then
sets each desk doc to status "queued_cloud") and the doc ids still waiting on images.
"""
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    desk, images = sys.argv[1:3]
    have = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(images, "*"))}
    staged, waiting = [], []
    for f in sorted(glob.glob(os.path.join(desk, "*.json"))):
        sid = os.path.splitext(os.path.basename(f))[0]
        doc = json.load(open(f, encoding="utf-8"))
        doc = doc.get("data", doc)
        out = os.path.join(ROOT, "outbox", sid)
        if doc.get("status") != "approved" or not doc.get("schedule_at") or os.path.exists(os.path.join(out, "post.json")):
            continue
        ids = [[u.rsplit("/", 1)[1] for u in row] for row in (doc.get("media_urls") or [])]
        missing = [b for row in ids for b in row if b not in have]
        if missing:
            waiting.append({"doc_id": sid, "missing_assets": missing})
            continue
        os.makedirs(out, exist_ok=True)
        media = []
        for r, row in enumerate(ids):
            paths = []
            for c, b in enumerate(row):
                fn = f"m{r}_{c}{os.path.splitext(have[b])[1]}"
                shutil.copyfile(have[b], os.path.join(out, fn))
                paths.append(f"outbox/{sid}/{fn}")
            media.append(paths)
        keep = {k: doc[k] for k in ("title", "feature", "kind", "parts", "reply", "quote_url") if k in doc}
        keep.update(status="approved", media=media, schedule_at=doc["schedule_at"])
        json.dump(keep, open(os.path.join(out, "post.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        staged.append({"doc_id": sid, "schedule_at": doc["schedule_at"]})
    print(json.dumps({"staged": staged, "waiting_on_images": waiting}, indent=1))


if __name__ == "__main__":
    main()
