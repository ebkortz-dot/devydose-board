#!/usr/bin/env bash
# Weekly NFL VOR refresh (v5): pull nflverse, find the latest complete week, run the
# walk-forward gate and the live values for that week.
#   usage: weekly_refresh.sh DATA_DIR OUT_DIR [WEEK]
# WEEK defaults to the latest regular-season week present in BOTH the 2026 weekly stats
# and the 2026 weekly rosters. Historical seasons are downloaded once and reused.
set -euo pipefail
D=${1:?data dir}; OUT=${2:?out dir}; WEEK=${3:-}
CODE=$(cd "$(dirname "$0")" && pwd)
REL=https://github.com/nflverse/nflverse-data/releases/download
mkdir -p "$D" "$OUT"
get() { curl -sSLf --retry 3 -o "$2.tmp" "$1" && mv "$2.tmp" "$2"; }
for y in $(seq 2012 2025); do
  [ -s "$D/stats_$y.csv" ] || get "$REL/stats_player/stats_player_week_$y.csv" "$D/stats_$y.csv"
  [ -s "$D/roster_weekly_$y.csv" ] || get "$REL/weekly_rosters/roster_weekly_$y.csv" "$D/roster_weekly_$y.csv"
done
get "$REL/stats_player/stats_player_week_2026.csv" "$D/stats_2026.csv"
get "$REL/weekly_rosters/roster_weekly_2026.csv" "$D/roster_weekly_2026.csv"
get "$REL/players/players.csv" "$D/players.csv"
if [ -z "$WEEK" ]; then
  WEEK=$(python3 -I - "$D" <<'EOF'
import sys, pandas as pd
d = sys.argv[1]
s = pd.read_csv(f'{d}/stats_2026.csv', low_memory=False, usecols=['week', 'season_type'])
r = pd.read_csv(f'{d}/roster_weekly_2026.csv', low_memory=False, usecols=['week', 'game_type'])
print(min(int(s[s.season_type == 'REG'].week.max()), int(r[r.game_type == 'REG'].week.max())))
EOF
)
fi
echo "[vor] week $WEEK"
cd "$OUT"
VOR_WEEK=$WEEK python3 "$CODE/vor_nfl.py" "$D" "$OUT" > "$OUT/gate_log.txt" 2>&1
VOR_WEEK=$WEEK python3 "$CODE/vor_live.py" "$D" "$OUT" > "$OUT/live_log.txt" 2>&1
python3 -I - "$OUT" "$WEEK" <<'EOF'
import json, sys
out, wk = sys.argv[1], int(sys.argv[2])
w = json.load(open(f'{out}/vor_gate_report.json'))['worst_of_two']
fails = {g: r for g, r in w.items() if r['vs_base0_dRho'] < 0 or r['vs_base0_dMAE'] > 0 or r['vs_naive_dRho'] < 0 or r['vs_naive_dMAE'] > 0}
json.dump({'week': wk, 'gate_cells': len(w), 'gate_fails': fails}, open(f'{out}/refresh_summary.json', 'w'), indent=1)
print('[vor] gate cells', len(w), 'fails', list(fails) or 'none')
EOF
echo "[vor] done: $OUT/nfl_vor_2026_w$(printf %02d "$WEEK").csv"
