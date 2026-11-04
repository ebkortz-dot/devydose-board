# Claude VOR cross-league model (research — NOT deployed)

- `code/` — current (v2) NFL model: `vor_nfl.py` (data, model, gate), `vor_live.py` (calibration, live 2026), `vor_bridge.py` (devy bridge, v1).
- `results/` — **v1** outputs (superseded for the NFL side; devy bridge is v1 and is DO NOT SHIP).
- `v2_nfl/{starter,waiver}/` — v2 NFL outputs after the independent review's fixes:
  replacement-baseline subtraction, isotonic recalibration on leave-one-season-out
  predictions, no-in-season model for players with no 2026 games.
- `review_v1/` — independent reviewer's scripts.
- Full write-up: Google Drive `cowork/Claude AU models/`.
