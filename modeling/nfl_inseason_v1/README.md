# NFL in-season value refresh, v1 (Claude, 2026-11-04)

Research artifact, NOT deployed. Full write-up: Google Drive `cowork/Claude AU models/`.

- `code/gate.py` — walk-forward gate, veterans (prior = previous-season PPG).
- `code/gate_np.py` — gate for players with no prior season (draft-capital prior).
- `code/refresh.py` — applies the blend to the Aug-11 `pro_values.json` (legacy P2.5 scale).
- `results/` — gate reports, the per-player-season evaluation rows (`gate_rows_N8.json`,
  usable to score any other model on the identical targets), the refreshed file and its audit.
- `MANIFEST.json` — byte counts and SHA-256 for every file here.

Reproduce: download nflverse `stats_player_week_{2012..2026}.csv` and `players.csv` into a
folder `nfl/`, put the live `pro_values.json` there as `pro_values_live.json`, then
`python3 -I code/gate.py nfl 8`, `python3 -I code/gate_np.py nfl 8`, `python3 -I code/refresh.py nfl 8 code`.
