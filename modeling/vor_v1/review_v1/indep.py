# Independent recomputation: points, replacement, target H, gate metrics.
import sys, os, math, json
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
D = S + '/nfl'
POS = ['QB','RB','WR','TE']
# ---- my own points: nflverse fantasy_points_ppr (4pt pass TD) + 2*pass TD
fr = []
for y in range(2012, 2027):
    d = pd.read_csv(f'{D}/stats_{y}.csv', low_memory=False)
    d = d[(d.season_type=='REG') & d.position.isin(POS)]
    fr.append(pd.DataFrame({'pid': d.player_id, 'y': y, 'w': d.week.astype(int), 'pos': d.position,
        'pts': d.fantasy_points_ppr.fillna(0) + 2*d.passing_tds.fillna(0), 'sttd': d.special_teams_tds.fillna(0),
        'frtd': d.fumble_recovery_tds.fillna(0) if 'fumble_recovery_tds' in d else 0}))
W = pd.concat(fr, ignore_index=True)
LINE = {'QB':12,'RB':24,'WR':36,'TE':12}
def repl(y, mode):
    s = W[W.y==y].groupby(['pid','pos']).pts.agg(['mean','size']).reset_index()
    s = s[s['size']>=6].sort_values('mean', ascending=False).reset_index(drop=True)
    st = set()
    for p in POS: st |= set(s[s.pos==p].pid.head(LINE[p]))
    r = s[~s.pid.isin(st)]; st |= set(r[r.pos!='QB'].pid.head(24))
    r = s[~s.pid.isin(st)]; st |= set(r.pid.head(12))
    out = {}
    for p in POS:
        n = int(((s.pos==p)&s.pid.isin(st)).sum())
        if mode=='waiver': out[p] = float(s[s.pos==p]['mean'].iloc[int(math.ceil(1.5*n))])
        else: out[p] = float(s[(s.pos==p)&~s.pid.isin(st)]['mean'].iloc[0])
        out[p+'_n'] = n
    return out
res = {}
for mode in ['starter','waiver']:
    RS = {y: repl(y, mode) for y in range(2013, 2026)}
    res[mode] = RS
    df = pd.DataFrame(RS).T
    print(mode); print(df.round(2).to_string())
    print('mean all', {p: round(df[p].mean(),2) for p in POS}, 'mean 2013-17', {p: round(df.loc[2013:2017,p].mean(),2) for p in POS},
          'mean 2013-20 (16g)', {p: round(df.loc[2013:2020,p].mean(),2) for p in POS}, 'mean 2021-25', {p: round(df.loc[2021:2025,p].mean(),2) for p in POS})
json.dump({m:{str(k):v for k,v in r.items()} for m,r in res.items()}, open(S+'/review_vor/repl_indep.json','w'), indent=1)
W.to_pickle(S+'/review_vor/W_indep.pkl')
