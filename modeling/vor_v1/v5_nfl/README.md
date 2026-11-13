# VOR v5 (NFL side): 2026 through Week 8, QB36, waiver replacement

**Canonical NFL values:** `v5_nfl/nfl_vor_2026_w08.csv`. These replace `v4_nfl/qb36`.

v5 fixes the findings from the independent review of v4 (all approved by Erik on 2026-11-09).

## 1. Inflated top end
- **v4:** above the top calibration point, values scaled up proportionally. Out of sample this over-predicted by roughly 1.5x.
- **v5 changes:**
  - The top calibration group must hold at least 25 player-seasons (`TOP_MIN`).
  - Above that point, values extend with a slope fitted on the top decile of out-of-fold predictions. The slope is bounded between 0 and the proportional slope.
- **Out of sample (both splits pooled):** predicted ÷ realized above the top point is now 1.04.
- **Result:** Smith-Njigba is still #1, at 457. His lead now comes from his projection, not from the scaling.

## 2. Historical positions
nflverse weekly stats label every past season with the player's current position. v5 reads each season's own weekly-roster position (regular-season mode; FB counts as RB).

## 3. IR
- `res` = roster status at Week 8 is RES, PUP or RSN. It is a model feature, so the history learns its effect on 2027 and 2028.
- POLICY (Erik): a player on reserve at Week 8 plays no more games this season, so his rest-of-season value is 0.
- In the live list, `res` comes from the latest 2026 status.
- Value on IR players fell from 479 (v4) to 333.

## 4. Naive baseline
- The naive baseline is now on the same scale as the target: 2.5 × (previous-season VOR − B × games).
- It is also re-centred in `all_recentred`.
- The real edge over naive is about 18 MAE, not the 34 reported for v4.

## Also
- `VOR_REPL` now defaults to `waiver`.
- The gate report records `repl_mode`, `qb_repl_rank`, `tail_slope` and `above_top_knot`.

## Gate (worst of two splits)
v5 beats the in-season-free model (base0) and naive in every group. Against base0:

| Group | dRho |
|---|---|
| All | +0.135 |
| QB | +0.054 |
| RB | +0.160 |
| WR | +0.158 |
| TE | +0.202 |
| Zero 2026 games | +0.004 (thin) |

## Still open (disclosed, not fixed)
- Replacement levels, baseline B and age-gate points use 2013–2025, including test seasons. This is a small leak.
- Display: re-centring spreads one third of the reference value into each window, so the rest-of-season column for an IR player shows a small negative number. The total is correct.

## Week 10 update (2026-11-13)
**Current NFL values:** `v5_nfl/w10/nfl_vor_2026_w10.csv`. Same v5 model and policies; nflverse data through Week 10.

- **Week setting:** the in-season week is now set with `VOR_WEEK`. Weeks 1..N are "early" and N+1..18 are the rest of the season. With `VOR_WEEK=8` the run reproduces the committed Week 8 values exactly.
- **Weekly job:** `code/weekly_refresh.sh DATA OUT [WEEK]` pulls nflverse, picks the latest complete week, then runs the gate and the live values.
- **Gate (worst of two splits):** all +0.142 dRho vs base0 (QB +0.057, RB +0.162, WR +0.165, TE +0.204).
  - One cell fails: players with no 2026 games, where dRho is −0.007 (MAE still improves by 5.1).
  - On the live board that group holds 3 points of 15,114 total value, so it is immaterial.
- **Why values fall:** values drop week to week because the rest-of-season window shrinks (8 games left, not 10).
  - Smith-Njigba is 400 (was 457), Gibbs 353, Nacua 311 (now on IR).
  - 8 QBs are in the top 24; 179 players are above 0.
