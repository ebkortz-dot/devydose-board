# VOR v4 (NFL side), 2026 through Week 8

## Changes from v3
- Positions are resolved from the 2026 roster, so Travis Hunter is a WR, not a CB.
- The model now trains on players with no early-season games. This fixes the overvaluation of players with no 2026 games (Fields was 161 in v3).
- Values are re-centred so the player at each position's replacement rank is worth 0. Display value is floored at 0, and players at or below 0 are flagged `droppable`.
- Age gates are later, which makes them more conservative (Erik): QB knots +2 years, RB/WR/TE knots +1 year.
- The top of the isotonic recalibration now uses proportional continuation, so elite players are no longer tied (Bowers 246, McBride 267).
- IR players are priced and flagged `IR`.
- The QB replacement rank is set with the `VOR_QB_RANK` environment variable. The default is 30, per Erik.

## QB replacement sweep
The walk-forward gate passes every cell at all four ranks.

| QB repl. rank | R_QB (PPG) | QBs in top 24 | QBs in top 60 | Josh Allen overall rank | Gate dRho, all / QB |
|---|---|---|---|---|---|
| QB30 | 14.3 | 3 | 12 | #15 | 0.148 / 0.084 |
| QB32 | 13.4 | 3 | 13 | #13 | 0.148 / 0.076 |
| QB34 | 12.3 | 4 | 16 | #6 | 0.142 / 0.054 |
| QB36 | 11.1 | 6 | 18 | #4 | 0.140 / 0.056 |

For comparison, superflex markets typically carry about 8–10 QBs in the top 24.
