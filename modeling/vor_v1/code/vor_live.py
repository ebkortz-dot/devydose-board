"""Claude VOR model, NFL side: calibration check + live 2026 values.

Fits on every complete row (seasons 2013-2023), predicts each 2026 player at the
end of Week 8: expected VOR over rest of 2026 + 2027 + 2028.
Roster gate (Erik, 2026-10-30): price only players whose LATEST 2026 weekly
roster status is ACT, or INA (game-day inactive but on the 53). RES (IR/PUP),
DEV (practice squad), CUT, RET and anyone not on a 2026 roster stay UNPRICED
with the reason. Active players with no 2026 games yet are priced from priors.
"""
import sys, json
import numpy as np, pandas as pd
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vor_nfl as V
D, OUT = sys.argv[1], sys.argv[2]
rows = V.rows

# ---- calibration on both splits ----
comp = rows[rows.H_complete]
calrep = {}
for nm, trsel, te in [('A', lambda d: d.y + 2 < 2018, range(2018, 2024)), ('B', lambda d: d.y >= 2018, range(2013, 2018))]:
    tr = comp[trsel(comp)]; ts = comp[comp.y.isin(te)].copy()
    ts['pred'], _ = V.predict(ts, V.fit(tr, True), True)
    ts['dec'] = pd.qcut(ts.pred.rank(method='first'), 10, labels=False)
    cal = ts.groupby('dec').agg(n=('H', 'size'), mean_pred=('pred', 'mean'), mean_H=('H', 'mean')).round(1)
    ts['r_season'] = ts.groupby('y').pred.rank(ascending=False)
    ts['r_pos'] = ts.groupby(['y', 'pos']).pred.rank(ascending=False)
    def ratio(q): return round(float(q.pred.sum() / q.H.sum()), 3)
    c = {'overall': ratio(ts), 'top12_per_season': ratio(ts[ts.r_season <= 12]), 'rank13_60': ratio(ts[ts.r_season.between(13, 60)]),
         'rank61_120': ratio(ts[ts.r_season.between(61, 120)]), 'TE_top3': ratio(ts[(ts.pos == 'TE') & (ts.r_pos <= 3)]),
         'TE_top12': ratio(ts[(ts.pos == 'TE') & (ts.r_pos <= 12)]), 'QB_top12': ratio(ts[(ts.pos == 'QB') & (ts.r_pos <= 12)])}
    calrep[nm] = c
    print(f'calibration split {nm} (pred/realized):', c)
    print(cal.to_string())
json.dump(calrep, open(f'{OUT}/calibration.json', 'w'), indent=1)

# ---- live 2026 ----
M = V.fit(comp, True)
M0 = V.fit(comp, False)   # no-in-season model, for players with no 2026 games (review finding 3)
ros = pd.read_csv(f'{D}/roster_weekly_2026.csv', low_memory=False)
ros = ros[ros.position.isin(V.POS)].sort_values('week').groupby('gsis_id').tail(1)
live = rows[rows.y == 2026].copy()
have = set(live.pid)
add = ros[(ros.status.isin(['ACT', 'INA', 'RES'])) & ~ros.gsis_id.isin(have)]
if len(add):
    extra = pd.DataFrame({'pid': add.gsis_id.values, 'y': 2026, 'pos': add.position.values, 'ge': 0, 'early': 0.0})
    for lag, nm in [(1, 'prior'), (2, 'prior2')]:
        v = [V.lookup(p, 2026-lag, 'ppg') for p in extra.pid]
        extra[nm] = [a if g >= 4 else np.nan for a, g in v]; extra[nm + '_g'] = [g for a, g in v]
    extra['lpick'] = np.log(extra.pid.map(V.pick).fillna(260.0))
    extra['age'] = [(pd.Timestamp('2026-09-01') - V.bd.get(p, pd.NaT)).days/365.25 if pd.notna(V.bd.get(p, pd.NaT)) else np.nan for p in extra.pid]
    live = pd.concat([live, extra], ignore_index=True)
live['age'] = live.groupby('pos').age.transform(lambda s: s.fillna(s.median()))
live['vor_value'], parts = V.predict(live, M, True)
v0, parts0 = V.predict(live, M0, False)
z = (live['ge'] == 0).values
live.loc[z, 'vor_value'] = v0[z]
for k in parts: parts[k][z] = parts0[k][z]
live['model'] = np.where(z, 'no_inseason(base0)', 'inseason')
for k in ('ros', 'y1', 'y2'):
    live['vor_' + k + '_exp'] = parts[k]; live['mu_' + k] = parts[k + '_mu']; live['g_' + k + '_exp'] = parts[k + '_g']
st = ros.set_index('gsis_id')
live['status'] = live.pid.map(st.status).fillna('NOT_ON_2026_ROSTER')
live['team'] = live.pid.map(st.team)
live['sleeper_id'] = live.pid.map(st.sleeper_id)
live['name'] = live.pid.map(V.P.display_name)
# Erik 2026-11-04: IR/PUP (RES) players are priced and flagged 'IR'
live['priced'] = live.status.isin(['ACT', 'INA', 'RES'])
live['flag'] = np.where(live.status == 'RES', 'IR', np.where(live.status == 'INA', 'inactive', ''))
live['rank'] = live.vor_value.where(live.priced).rank(ascending=False, method='first')
live = live.sort_values('vor_value', ascending=False)
cols = ['pid', 'sleeper_id', 'name', 'pos', 'team', 'status', 'flag', 'priced', 'rank', 'vor_value', 'model', 'vor_ros_exp', 'vor_y1_exp', 'vor_y2_exp',
        'mu_ros', 'mu_y1', 'mu_y2', 'g_ros_exp', 'g_y1_exp', 'g_y2_exp', 'ge', 'early', 'prior', 'prior2', 'age']
live[cols].to_csv(f'{OUT}/nfl_vor_2026_w08.csv', index=False, float_format='%.3f')
print('\nlive rows', len(live), 'priced', int(live.priced.sum()), live.status.value_counts().to_dict())
show = live[live.priced].head(30)
print(show[['name', 'pos', 'team', 'vor_value', 'vor_ros_exp', 'vor_y1_exp', 'vor_y2_exp', 'mu_y1', 'age']].round(1).to_string(index=False))
print('\nTop unpriced (roster gate):')
print(live[~live.priced].head(15)[['name', 'pos', 'team', 'status', 'vor_value']].round(1).to_string(index=False))
