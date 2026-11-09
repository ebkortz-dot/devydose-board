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
