#!/usr/bin/env python3
"""
fetch_command_center.py -- copy the Alpha Command Center pages into website/public/.

Pulls five files from the public devydose-board GitHub repo, pinned to one
commit, checks every file's SHA-256 against the list below, and only then
writes them into public/. It never deploys: after it runs, publish with the
usual deploy_netlify.py.

  python3 fetch_command_center.py                 # dry run: download + verify, write nothing
  python3 fetch_command_center.py --apply         # verify, then write into ../../public
  python3 fetch_command_center.py --apply --public /path/to/website/public

Refuses to overwrite a file that already exists in public/ with different
content (pass --force only if you mean to replace it). Pure stdlib.
"""
import argparse, hashlib, os, sys, urllib.request

COMMIT = "32e17fca60dd0be2ae3d92ff422fe29ef3dee2d5"
BASE = f"https://raw.githubusercontent.com/ebkortz-dot/devydose-board/{COMMIT}/staging/command-center/"
FILES = {
    "command.html":            "fdf87dec0eb32c1c1cc8a23b55d891a31add8d92571e22f587395bda234f7f6c",
    "manifest.webmanifest":    "a9910e2794fcc14f32a9162cea993abae1f1ddf3a391bcde0f3e6b31ab633ec8",
    "assets/app-icon-180.png": "e3180bc5fe1bdaedb183c2a00448d9a52859b40a16f940e7436e311c6dbd987a",
    "assets/app-icon-192.png": "ed21b05241c7b2ae53991fd79caf3a43cd4273feaa39cc53f7ca6f402e16e781",
    "assets/app-icon-512.png": "75cd6be6cb9f60a20bbbf293ac60a6481574bb7617ca2974f91c69bd9a385a08",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the verified files into public/")
    ap.add_argument("--public", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "public"))
    ap.add_argument("--force", action="store_true", help="replace a differing file already in public/")
    a = ap.parse_args()
    public = os.path.abspath(a.public)
    if a.apply and not os.path.isdir(public):
        sys.exit(f"public/ not found at {public} -- pass --public")

    got, bad = {}, []
    for rel, want in FILES.items():
        data = urllib.request.urlopen(BASE + rel, timeout=60).read()
        have = hashlib.sha256(data).hexdigest()
        ok = have == want
        print(f"{'OK  ' if ok else 'FAIL'} {rel:26} {len(data):>7} bytes  sha256 {have[:12]}")
        if ok:
            got[rel] = data
        else:
            bad.append(rel)
    if bad:
        sys.exit(f"{len(bad)} file(s) failed verification; nothing written.")

    clashes = []
    for rel, data in got.items():
        dest = os.path.join(public, rel)
        if os.path.exists(dest) and open(dest, "rb").read() != data:
            clashes.append(rel)
    if clashes and not a.force:
        sys.exit("These already exist in public/ with different content: " + ", ".join(clashes) + " -- nothing written (use --force to replace).")

    if not a.apply:
        print(f"\nDry run: all {len(got)} files verified. Re-run with --apply to write them into {public}")
        return
    for rel, data in got.items():
        dest = os.path.join(public, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        print(f"wrote {dest}")
    print("\nDone. Not deployed yet -- publish with the usual deploy_netlify.py, then check /command.")


if __name__ == "__main__":
    main()
