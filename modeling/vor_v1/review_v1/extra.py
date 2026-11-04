import sys, os
S = '/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
OUTD = S + '/review_vor/extra_' + os.environ.get('VOR_REPL', 'starter'); os.makedirs(OUTD, exist_ok=True)
sys.argv = ['x', S + '/nfl', OUTD]
sys.path.insert(0, '/home/user/devydose-board/modeling/vor_v1/code')
import numpy as np, pandas as pd
import vor_nfl as V
def sp(a, b): return float(np.corrcoef(pd.Series(np.asarray(a)).rank(), pd.Series(np.asarray(b)).rank())[0,1])
rows = V.rows; comp = rows[rows.H_complete]
# 1) gate on future seasons only (y1+y2), excluding ROS
for nm, sel, te in [('A', lambda d: d.y+2 < 2018, range(2018, 2024)), ('B', lambda d: d.y >= 2018, range(2013, 2018))]:
    tr = comp[sel(comp)]; ts = comp[comp.y.isin(te)].copy()
    M1 = V.fit(tr, True); M0 = V.fit(tr, False)
    _, p1 = V.predict(ts, M1, True); _, p0 = V.predict(ts, M0, False)
    Hf = (ts.vor_y1 + ts.vor_y2).values; Hr = ts.vor_ros.values
    f1 = p1['y1'] + p1['y2']; f0 = p0['y1'] + p0['y2']
    print(nm, 'FUTURE y1+y2: MAE pred %.2f base0 %.2f | rho pred %.4f base0 %.4f' % (np.abs(f1-Hf).mean(), np.abs(f0-Hf).mean(), sp(f1, Hf), sp(f0, Hf)))
    print(nm, 'ROS only:     MAE pred %.2f base0 %.2f | rho pred %.4f base0 %.4f' % (np.abs(p1['ros']-Hr).mean(), np.abs(p0['ros']-Hr).mean(), sp(p1['ros'], Hr), sp(p0['ros'], Hr)))
    print(nm, 'share of realized H from ROS %.3f' % (Hr.sum()/(Hr.sum()+Hf.sum())))
# 2) training support of ge
print('training ge distribution', comp['ge'].value_counts().sort_index().to_dict())
# 3) live: ge=0 players, full model vs no-in-season model
lv = pd.read_csv(S + f"/review_vor/rerun_{os.environ.get('VOR_REPL','starter')}/nfl_vor_2026_w08.csv")
M1 = V.fit(comp, True); M0 = V.fit(comp, False)
print('live-fit scales', {p: round(M1[p]['scale'], 3) for p in V.POS})
# rebuild live frame as in vor_live for ge==0 players
z = lv[lv['ge'] == 0][['pid','name','pos','vor_value','prior','prior2','age']].copy()
z['y'] = 2026; z['ge'] = 0; z['early'] = 0.0
z['prior_g'] = [V.lookup(p, 2025, 'ppg')[1] for p in z.pid]
z['lpick'] = np.log(z.pid.map(V.pick).fillna(260.0))
z['b0'], _ = V.predict(z, M0, False); z['m1'], _ = V.predict(z, M1, True)
z['pick'] = z.pid.map(V.pick)
print(z.sort_values('b0', ascending=False).head(15)[['name','pos','pick','age','vor_value','m1','b0']].round(1).to_string(index=False))
print('ge=0 sum vor_value %.1f vs base0 %.1f' % (z.m1.sum(), z.b0.sum()))
# 4) value of a player projected exactly at replacement (convexity floor)
for p in V.POS:
    a, b = V.SIG[p]; r = V.R[p]
    s_w = a + b*r
    for sres in (0.0, 4.0):
        sig = np.sqrt(s_w**2 + sres**2)
        print(p, 'mu=R=%.2f weekly sd %.2f proj_sd %.1f -> E[VOR]/wk %.2f, x 40 games = %.0f' % (r, s_w, sres, float(V.ev_pos(np.array([r]), np.array([sig]), r)[0]), 40*float(V.ev_pos(np.array([r]), np.array([sig]), r)[0])))
    print(p, 'model residual sd', {w: round(M1[p][w + '_s'], 2) for w in ('ros','y1','y2')})
