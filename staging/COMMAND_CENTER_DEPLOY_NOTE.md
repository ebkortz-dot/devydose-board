# Alpha Command Center — staged for deploy (NOT live)

Staged 2026-10-28 by a Claude helper session at Erik's request (supersedes the
2026-10-27 staging, which had a separate Sleeper page). Nothing has been
written to `website/public/` and nothing has been deployed.

## What it is
ONE public page, read-only (no login, nothing written to Fantrax or Sleeper):

`command.html` -> /command — **Alpha Command Center**: every C2C, dynasty,
redraft and college fantasy league a user plays, on Fantrax (league URL) and
Sleeper (username), in one place. A **Viewing** switcher groups the Fantrax
league set, each Sleeper league, and the linked C2C (Fantrax college + Sleeper
NFL as one franchise per manager). Tabs follow the view:
- Power Rankings · My Roster (AU value; redraft Sleeper leagues use next-3-week projections)
- Start / Sit (Sleeper: projections re-scored on each league's scoring_settings; optimal legal lineup)
- Trade Finder (shop / target / auto; college + NFL; cross-app offers written as one deal, two halves)
- Free Agents (college: Fantrax's own FA status; NFL on Sleeper: projections, 24h trending adds, FAAB, drop candidates)
- All Leagues (every Sleeper lineup checked at once; player exposure across Fantrax + Sleeper)

Plus `manifest.webmanifest` and `assets/app-icon-{180,192,512}.png` (installs
to a phone home screen as "AU Command"). None of these paths exist on the live
site (checked 404), so nothing is overwritten. There is no separate Sleeper
page any more.

## Data it reads
`/board_values.json` and `/pro_values.json` from the live site (root-absolute),
so it always shows the current board. No new data files.
POLICY (not fitted, not backtested): trade "fair" band is user-set ±5–20%
(default 10%); 2-for-1s need both pieces ≥ 25% of the single player and neither
better than him; positional need/surplus = bottom/top third by summed top-4
value at the position.

## Tested (2026-10-28, headless Chromium)
Against both the repo data and copies of the live v5.1 board_values.json
(2026-10-25), live pro_values.json and live theme.css:
- Sleeper user ekballer: all 28 leagues in the switcher; start/sit, waivers and
  the all-leagues lineup check on each; a redraft league switches to projections.
- Fantrax "Baller's C2C" added after Sleeper -> C2C partner auto-picked (Sleeper
  "Ballers C2C"), 14/14 managers paired automatically.
- Reload restores the view and pairings; links saved by the earlier build
  migrate; Disconnect clears cleanly.
- 0 console errors; no horizontal scroll at 390px.
- ID coverage (exact name + position; duplicates resolved by school/team, never
  guessed): college 430/444 on Fantrax, NFL 511/528 on Fantrax, 514/528 on Sleeper.

## To deploy (prime / Erik)
1. From this folder: `python3 fetch_command_center.py` — dry run: downloads the five
   files from GitHub (pinned to commit `32e17fc`) and checks every SHA-256.
2. `python3 fetch_command_center.py --apply` — writes them into `website/public/`
   (refuses to overwrite anything that differs).
3. Run the usual `deploy_netlify.py`, then open /command.

Fallback without the script: download the same files from
https://github.com/ebkortz-dot/devydose-board/tree/32e17fca60dd0be2ae3d92ff422fe29ef3dee2d5/staging/command-center
into `website/public/` (keep the `assets/` subfolder).

## Not done here (prime-only per the coordination rules)
- **Site menu:** add "Command Center" (/command) to the shared nav in the page
  generators. The page already carries the full live menu including it.
- **STATE / HANDOFF:** record the ship via coord.ship(...) with the deploy id.
- No netlify.toml change needed — the site's pretty URLs serve /command for command.html.
