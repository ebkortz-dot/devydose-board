import sys, os, math, json
S = '/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
OUTD = S + '/review_vor/gate_' + os.environ.get('VOR_REPL', 'starter'); os.makedirs(OUTD, exist_ok=True)
sys.argv = ['x', S + '/nfl', OUTD]
sys.path.insert(0, '/home/user/devydose-board/modeling/vor_v1/code')
import numpy as np, pandas as pd
import vor_nfl as V
def spearmanr(a,b):
    class R: pass
    r=R(); r.correlation=float(np.corrcoef(pd.Series(np.asarray(a)).rank().values, pd.Series(np.asarray(b)).rank().values)[0,1]); return r
POS = V.POS
Wi = pd.read_pickle(S + '/review_vor/W_indep.pkl')
# compare points
m = V.W.merge(Wi, on=['pid','y','w'], suffixes=('_a','_i'))
dd = (m.pts_a - m.pts_i)
print('points rows', len(V.W), len(Wi), 'matched', len(m), '| |diff|>0.01:', int((dd.abs()>0.01).sum()), 'explained by ST/FR TDs:', int(((dd.abs()>0.01) & ((m.sttd+m.frtd)>0)).sum()))
rows = V.rows.copy()
def H_from(Rd, W=V.W):
    W = W[['pid','y','w','pos','pts']].copy(); W['v'] = np.maximum(0, W.pts - W.pos.map(Rd))
    ros = W[W.w > 8].groupby(['pid','y']).v.sum(); seas = W.groupby(['pid','y']).v.sum()
    k = list(zip(rows.pid, rows.y))
    a = np.array([ros.get(t, 0.0) for t in k]); b = np.array([seas.get((p,y+1), 0.0) for p,y in k]); c = np.array([seas.get((p,y+2), 0.0) for p,y in k])
    return a+b+c
Hi = H_from(V.R, Wi)
print('target H: author vs independent (own points) max|diff| %.2f, mean|diff| %.3f, corr %.6f' % (np.abs(rows.H - Hi).max(), np.abs(rows.H - Hi).mean(), np.corrcoef(rows.H, Hi)[0,1]))
def metrics(ts, colp, colH='H'):
    out = {}
    for grp in ['all'] + POS + ['top200']:
        if grp == 'all': q = ts
        elif grp == 'top200': q = ts[ts.pred.rank(ascending=False) <= 200*ts.y.nunique()]
        else: q = ts[ts.pos == grp]
        out[grp] = {c: (float(np.mean(np.abs(q[c]-q[colH]))), float(spearmanr(q[c], q[colH]).correlation)) for c in colp}
    return out
def run(trsel, te, Rtrain=None, Hcol='H', purgeB=False):
    comp = rows[rows.H_complete].copy()
    tr = comp[trsel(comp)].copy(); ts = comp[comp.y.isin(te)].copy()
    R0 = dict(V.R)
    if Rtrain is not None:
        V.R.update(Rtrain)
        Htr = H_from(V.R); tr['H'] = Htr[tr.index.map(lambda i: rows.index.get_loc(i))]
    M1 = V.fit(tr, True); M0 = V.fit(tr, False)
    ts['pred'], _ = V.predict(ts, M1, True); ts['base0'], _ = V.predict(ts, M0, False)
    V.R.clear(); V.R.update(R0)
    return ts, M1
splits = {'A': (lambda d: d.y + 2 < 2018, range(2018, 2024)), 'B': (lambda d: d.y >= 2018, range(2013, 2018)),
          'B_purged(train y>=2020)': (lambda d: d.y >= 2020, range(2013, 2018))}
allres = {}
for nm, (sel, te) in splits.items():
    ts, M1 = run(sel, te)
    allres[nm] = metrics(ts, ['pred','base0'])
    print(nm, 'scales', {p: round(M1[p]['scale'],3) for p in POS})
    if nm == 'A': tsA = ts
    if nm == 'B': tsB = ts
def worst(a, b):
    return {g: {'dMAE': round(max(a[g]['pred'][0]-a[g]['base0'][0], b[g]['pred'][0]-b[g]['base0'][0]),2),
                'dRho': round(min(a[g]['pred'][1]-a[g]['base0'][1], b[g]['pred'][1]-b[g]['base0'][1]),4)} for g in a}
print('WORST A/B (my metrics):'); [print('  ', g, v) for g, v in worst(allres['A'], allres['B']).items()]
print('WORST A/B_purged:'); [print('  ', g, v) for g, v in worst(allres['A'], allres['B_purged(train y>=2020)']).items()]
for nm in allres: print(nm, {g: {c: (round(v[c][0],2), round(v[c][1],4)) for c in v} for g, v in allres[nm].items() if g in ('all','top200')})
# ---- train-only R for split A: replacement from 2013-2017 only, used in model and train target
RS = {y: V.repl_season(y) for y in range(2013, 2018)}
RA = {p: float(np.mean([RS[y][p] for y in RS])) for p in POS}
print('R full', {p: round(V.R[p],2) for p in POS}, 'R train-only(2013-17)', {p: round(RA[p],2) for p in POS})
ts, _ = run(splits['A'][0], splits['A'][1], Rtrain=RA)
r1 = metrics(ts, ['pred','base0'])
print('A with train-only R (model+train target), evaluated on full-R target:', {g: {c: (round(v[c][0],2), round(v[c][1],4)) for c in v} for g, v in r1.items()})
print('   vs default A:', {g: {c: (round(v[c][0],2), round(v[c][1],4)) for c in v} for g, v in allres['A'].items()})
# ---- calibration deciles A and B, with ratio
for nm, ts in [('A', tsA), ('B', tsB)]:
    ts = ts.copy(); ts['dec'] = pd.qcut(ts.pred.rank(method='first'), 10, labels=False)
    c = ts.groupby('dec').agg(n=('H','size'), pred=('pred','mean'), H=('H','mean'), base0=('base0','mean'))
    c['ratio'] = c.pred / c.H
    print('calib', nm); print(c.round(2).to_string())
    t = ts.sort_values('pred', ascending=False)
    for k in (12, 24, 50, 100):
        q = t.groupby('y').head(k)
        print(f'  top{k}/season: pred {q.pred.mean():.1f} realized {q.H.mean():.1f} ratio {q.pred.mean()/q.H.mean():.3f}', {p: round(q[q.pos==p].pred.mean()/q[q.pos==p].H.mean(),3) for p in POS})
    # bias by position in top decile
    top = ts[ts.dec==9]; print('  top decile by pos pred/H', {p: (int((top.pos==p).sum()), round(top[top.pos==p].pred.mean()/top[top.pos==p].H.mean(),3)) for p in POS})
tsA.to_pickle(OUTD + '/tsA.pkl'); tsB.to_pickle(OUTD + '/tsB.pkl')
