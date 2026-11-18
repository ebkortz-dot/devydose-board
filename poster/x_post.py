"""Post an APPROVED Post Desk thread to X (DevyDose) with the official API (OAuth 1.0a user context).

    python x_post.py --check                       # verify the write keys (GET /2/users/me, posts nothing)
    python x_post.py --file post.json --dry-run    # show exactly what would be posted, no API calls
    python x_post.py --file post.json              # post it: parts as a reply chain, then the link reply

Media (optional): "media" is a list parallel to "parts"; media[i] is a list of up to 4 local PNG/JPG paths
(each <= 5 MB) attached to part i. All media is validated, then UPLOADED FIRST (X media upload endpoint, OAuth
1.0a user context; multipart body is not part of the signature), and only then is the thread posted with
"media": {"media_ids": [...]} on each part. --dry-run lists the media per part and makes no API call; it also
previews drafts (non-approved docs) but never posts them.

post.json is one Post Desk document (the `posts` collection): it must have "status": "approved" and a
non-empty "parts" list. Each part must be <= 280 X-weighted characters. Output: a JSON line with the
posted ids and the URL of post 1, so the caller can mark the desk doc as posted.

Keys come from env (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET) or from the
'API Keys AU.txt' headings "X API Key", "X API Secret", "X Access Token", "X Access Secret".
They are never printed. Never run this for a post Erik has not approved.
"""
import argparse, base64, hashlib, hmac, json, os, re, secrets, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = r"H:\My Drive\cowork\Alpha Universe"
KEYFILE = os.path.join(ROOT, "API Keys AU.txt")
API = "https://api.x.com/2"
HEADS = {"X API Key": "X_API_KEY", "X API Secret": "X_API_SECRET", "X Access Token": "X_ACCESS_TOKEN", "X Access Secret": "X_ACCESS_SECRET"}
LIMIT = 280
MEDIA_UPLOAD_V2 = "https://api.x.com/2/media/upload"
MEDIA_UPLOAD_V11 = "https://upload.twitter.com/1.1/media/upload.json"
MEDIA_MAX_BYTES = 5 * 1024 * 1024
MEDIA_PER_POST = 4
MAGIC = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg"}


def load_keys():
    out = {env: os.environ.get(env, "").strip() for env in HEADS.values()}
    if not all(out.values()) and os.path.exists(KEYFILE):
        want, lines = None, [l.strip() for l in open(KEYFILE, encoding="utf-8", errors="replace")]
        for s in lines:
            key = s.strip("[]").strip()
            if key in HEADS:
                want = HEADS[key]
                continue
            if want and s:
                out[want] = out[want] or s
                want = None
    missing = [k for k, v in HEADS.items() if not out[v]]
    if missing:
        raise SystemExit("HARD STOP — X posting keys missing: " + ", ".join(missing) + " (add them to 'API Keys AU.txt').")
    return out


def xlen(t):
    t = re.sub(r"https?://\S+", "x" * 23, t or "")
    n = 0
    for ch in t:
        cp = ord(ch)
        if cp in (0xFE0F, 0x200D):
            continue
        light = cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F or 0x2032 <= cp <= 0x2037
        n += 1 if light else 2
    return n


def _q(s):
    return urllib.parse.quote(str(s), safe="~-._")


def oauth_header(method, url, k, query=None):
    o = {"oauth_consumer_key": k["X_API_KEY"], "oauth_nonce": secrets.token_hex(16), "oauth_signature_method": "HMAC-SHA1",
         "oauth_timestamp": str(int(time.time())), "oauth_token": k["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
    params = {**o, **(query or {})}   # JSON bodies are not part of the signature
    base = "&".join([method.upper(), _q(url), _q("&".join(f"{_q(a)}={_q(b)}" for a, b in sorted(params.items())))])
    key = f"{_q(k['X_API_SECRET'])}&{_q(k['X_ACCESS_SECRET'])}"
    o["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_q(a)}="{_q(b)}"' for a, b in sorted(o.items()))


def call(method, path, k, body=None, query=None):
    url = API + path
    full = url + ("?" + urllib.parse.urlencode(query) if query else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(full, data=data, method=method, headers={
        "Authorization": oauth_header(method, url, k, query), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, {"raw": txt[:300]}


def media_plan(doc, n_parts):
    """Validate doc["media"] -> list (len n_parts) of lists of (path, mime, bytes). Raises SystemExit on any problem."""
    media = doc.get("media") or []
    if len(media) > n_parts and any(media[n_parts:]):
        raise SystemExit(f"REFUSED — media given for {len(media)} parts but only {n_parts} parts.")
    plan, errs = [], []
    for i in range(n_parts):
        items = (media[i] if i < len(media) else None) or []
        if isinstance(items, str):
            items = [items]
        if len(items) > MEDIA_PER_POST:
            errs.append(f"post {i + 1}: {len(items)} media (max {MEDIA_PER_POST})")
        row = []
        for p in items:
            if not os.path.isfile(p):
                errs.append(f"post {i + 1}: missing file {p}")
                continue
            if os.path.splitext(p)[1].lower() not in (".png", ".jpg", ".jpeg"):
                errs.append(f"post {i + 1}: not PNG/JPG {p}")
                continue
            size = os.path.getsize(p)
            if size > MEDIA_MAX_BYTES:
                errs.append(f"post {i + 1}: {size:,} bytes > 5 MB {p}")
                continue
            with open(p, "rb") as f:
                head = f.read(8)
            mime = next((m for sig, m in MAGIC.items() if head.startswith(sig)), None)
            if not mime:
                errs.append(f"post {i + 1}: file content is not PNG/JPG {p}")
                continue
            row.append((p, mime, size))
        plan.append(row)
    if errs:
        raise SystemExit("REFUSED — media problems: " + "; ".join(errs))
    return plan


def _multipart(fields, files):
    boundary = "----devydose" + secrets.token_hex(12)
    out = []
    for name, val in fields.items():
        out += [f"--{boundary}".encode(), f'Content-Disposition: form-data; name="{name}"'.encode(), b"", str(val).encode()]
    for name, (fn, mime, data) in files.items():
        out += [f"--{boundary}".encode(),
                f'Content-Disposition: form-data; name="{name}"; filename="{os.path.basename(fn)}"'.encode(),
                f"Content-Type: {mime}".encode(), b"", data]
    out += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(out), f"multipart/form-data; boundary={boundary}"


def upload_media(path, mime, k):
    """Simple (non-chunked) image upload: v2 endpoint first, v1.1 as fallback. Multipart bodies are NOT signed."""
    data = open(path, "rb").read()
    tries = [(MEDIA_UPLOAD_V2, {"media_category": "tweet_image"}, lambda d: (d.get("data") or {}).get("id")),
             (MEDIA_UPLOAD_V11, {"media_category": "tweet_image"}, lambda d: d.get("media_id_string"))]
    last = None
    for url, fields, pick in tries:
        body, ctype = _multipart(fields, {"media": (path, mime, data)})
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": oauth_header("POST", url, k), "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
                status = r.status
            mid = pick(d)
            if mid:
                return str(mid)
            last = (url, status, str(d)[:300])
        except urllib.error.HTTPError as e:
            last = (url, e.code, e.read().decode("utf-8", "replace")[:300])
    raise RuntimeError(f"media upload failed for {os.path.basename(path)}: {last}")


def check(k):
    # GET is safe to repeat: retry transient network failures (e.g. WinError 10060 on 2026-10-17)
    for attempt in range(4):
        try:
            st, d = call("GET", "/users/me", k)
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 3:
                print(json.dumps({"ok": False, "network_error": str(e)[:200]}))
                return 1
            time.sleep(10 * (attempt + 1))
    if st == 200:
        print(json.dumps({"ok": True, "username": d["data"]["username"]}))
        return 0
    print(json.dumps({"ok": False, "http": st, "detail": d}))
    return 1


def post_thread(doc, k, dry):
    if doc.get("status") != "approved" and not dry:
        raise SystemExit(f"REFUSED — post status is {doc.get('status')!r}, not 'approved'.")
    parts = [p.strip() for p in doc.get("parts", []) if p and p.strip()]
    reply = (doc.get("reply") or "").strip()
    if not parts:
        raise SystemExit("REFUSED — no parts to post.")
    over = [i + 1 for i, p in enumerate(parts + ([reply] if reply else [])) if xlen(p) > LIMIT]
    if over:
        raise SystemExit(f"REFUSED — over {LIMIT} characters: post(s) {over}.")
    seq = parts + ([reply] if reply else [])
    plan = media_plan(doc, len(parts)) + [[]]
    n_media = sum(len(m) for m in plan)
    if dry:
        if doc.get("status") != "approved":
            print(f"(preview only: status is {doc.get('status')!r}; a real run REFUSES anything not 'approved')")
        for i, p in enumerate(seq, 1):
            print(f"--- {i}/{len(seq)} ({xlen(p)} chars){' [link reply]' if reply and i == len(seq) else ''}\n{p}")
            for path, mime, size in plan[i - 1]:
                print(f"    [media] {os.path.basename(path)} ({mime}, {size / 1024:,.0f} KB)  {path}")
        print(json.dumps({"dry_run": True, "status": doc.get("status"), "posts": len(seq), "media": n_media,
                          "est_cost_usd": round(0.015 * len(parts) + (0.20 if reply else 0), 3)}))
        return 0
    media_ids = []
    for row in plan:          # upload everything BEFORE the first post, so a bad file never leaves half a thread
        ids_i = []
        for path, mime, _ in row:
            try:
                ids_i.append(upload_media(path, mime, k))
            except RuntimeError as e:
                print(json.dumps({"ok": False, "stage": "media_upload", "detail": str(e), "posted_ids": []}))
                return 1
        media_ids.append(ids_i)
    ids, prev = [], None
    for i, text in enumerate(seq, 1):
        body = {"text": text}
        if media_ids[i - 1]:
            body["media"] = {"media_ids": media_ids[i - 1]}
        elif i == 1 and doc.get("quote_url"):     # post 1 quotes another post (e.g. GOTW receipts quote the GOTW thread)
            m = re.search(r"/status/(\d+)", doc["quote_url"])
            if m:
                body["quote_tweet_id"] = m.group(1)
        if prev:
            body["reply"] = {"in_reply_to_tweet_id": prev}
        st, d = call("POST", "/tweets", k, body=body)
        if st not in (200, 201):
            print(json.dumps({"ok": False, "failed_at": i, "posted_ids": ids, "http": st, "detail": d}))
            return 1
        prev = d["data"]["id"]
        ids.append(prev)
        time.sleep(1.5)
    st, me = call("GET", "/users/me", k)
    user = me.get("data", {}).get("username", "i") if st == 200 else "i"
    print(json.dumps({"ok": True, "posted_ids": ids, "posted_url": f"https://x.com/{user}/status/{ids[0]}"}))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.file:
        doc = json.load(open(a.file, encoding="utf-8"))
        doc = doc.get("data", doc)
        if a.dry_run:
            return post_thread(doc, None, True)
        return post_thread(doc, load_keys(), False)
    if a.check:
        return check(load_keys())
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
