# Alpha Command Center — staged for deploy (NOT live)

Staged 2026-10-27 by a Claude helper session at Erik's request. Nothing has been
written to `website/public/` and nothing has been deployed.

## What it is
Two new public tools, read-only (no login, nothing written to Fantrax or Sleeper):

| Page | Live URL after deploy | What it does |
|---|---|---|
| `command.html` | /command | **Alpha Command Center** — C2C, dynasty and CFF leagues on one AU value scale. Fantrax (league URL) and/or Sleeper (username). Power rankings, roster view, mass trade finder (college + NFL, cross-app offers), AU-board free agents. |
| `sleeper.html` | /sleeper | **Sleeper Roster Manager** — weekly start/sit scored on each league's settings, waivers + FAAB, trade finder, all-leagues lineup check. |

Plus `manifest.webmanifest` and `assets/app-icon-{180,192,512}.png` so the
tools install to a phone home screen ("AU Command"). None of these six paths
exist on the live site today (all checked 404 on 2026-10-27), so nothing is
overwritten.

## Data it reads
`/board_values.json` and `/pro_values.json` from the live site (root-absolute
paths), so it always shows the current board. No new data files.

## Tested (2026-10-27, headless Chromium, live data copies)
- Live v5.1 `board_values.json` (2026-10-25) + live `pro_values.json` + live `theme.css`.
- Fantrax "Baller's C2C" (14-team college) alone; Sleeper "Dynasty Hogz" alone;
  Fantrax Baller's C2C + Sleeper "Ballers C2C" linked — 14/14 managers paired
  automatically. Sleeper Roster Manager on user ekballer (28 leagues).
- No console errors; no horizontal scroll at 390px.
- ID coverage (exact name + position; duplicates resolved by school/team, never
  guessed): college 430/444 on Fantrax, NFL 511/528 on Fantrax, 514/528 on Sleeper.

## To deploy (prime / Erik)
1. From this folder: `python3 fetch_command_center.py` — dry run: downloads the six
   files from GitHub (pinned to commit `778774a`) and checks every SHA-256.
2. `python3 fetch_command_center.py --apply` — writes them into `website/public/`
   (refuses to overwrite anything that differs).
3. Run the usual `deploy_netlify.py`, then open /command and /sleeper.

Fallback without the script: download the same files from
https://github.com/ebkortz-dot/devydose-board/tree/778774a67a928ad72bce690a96a148f3c333e5af/staging/command-center
into `website/public/` (keep the `assets/` subfolder).

## Not done here (prime-only per the coordination rules)
- **Site menu:** the shared nav on generated pages doesn't list Command Center yet;
  it needs adding in the page generators. The new pages already carry the full
  live menu including Command Center, so they're reachable by direct link.
- **STATE / HANDOFF:** record the ship in `ALPHA_UNIVERSE_STATE.md` via the usual
  ship step when it deploys.
- Optional `netlify.toml` redirects aren't needed — the site's pretty URLs already
  serve `/command` for `command.html`.
