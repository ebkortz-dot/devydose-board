"""Claude VOR model, college side: bridge v86w devy values onto the NFL VOR scale.

The live Trade Lab feed (rookie-anchor-feed.json, model au_canonical_v86w ...)
prices devy and NFL players on one rookie-anchored index (profile ppr6_te0).
Erik's rule: a devy player's value in his draft year = his value entering his
rookie NFL season. So for each position, fit a monotone (isotonic / PAV) curve
index -> NFL VOR on the NFL players priced in BOTH the feed and the Claude NFL
VOR model, then read devy players off that curve.

Devy ordering is brought to Week 9: the feed's devy index is Week 7, so each
position's Week-7 index distribution is re-assigned to players by their Week-9
v86w position rank (snapshot 2026_w09_v86w). Players not in the Week-9 snapshot
keep their Week-7 index. Feed-unpriced devy players stay unpriced.

NOT applied (open policy, Erik): a discount for years until the NFL, and
non-selection risk. The feed's devy index is conditional on being drafted
(its own limitation note), so devy values here are too.
Test: leave-one-out on the NFL players -- predict each one's VOR from the curve
fitted without him; Spearman + MAE; and the bias on 2026 rookies specifically.
"""
import sys, json
import numpy as np, pandas as pd
FEED, W09, NFLVOR, OUT, TAG = sys.argv[1:6]
PROF = 'ppr6_te0'
POS = ['QB', 'RB', 'WR', 'TE']

feed = json.load(open(FEED)); A = feed['assets']
def fv(a):
    v = a['values'].get(PROF, {})
    return (v.get('value') if v.get('status') == 'priced' else None), v.get('status'), v.get('reason')
nv = pd.read_csv(NFLVOR).set_index('pid')

# ---- training pairs: NFL players priced in both ----
pairs = []
for a in A:
    if a['population'] != 'nfl': continue
    idx, st, _ = fv(a)
    if idx is None or a['id'] not in nv.index: continue
    r = nv.loc[a['id']]
    if not r.priced: continue
    pairs.append(dict(pid=a['id'], name=a['name'], pos=a['position'], idx=idx, vor=r.vor_value, rookie=a.get('rookie_season') == 2026))
pairs = pd.DataFrame(pairs)

def pav(x, y):
    """isotonic increasing fit; returns knots (x sorted, fitted y)."""
    o = np.argsort(x); x, y = np.asarray(x)[o], np.asarray(y, float)[o]
    blocks = [[v, 1.0] for v in y]
    vals, wts, idxs = [], [], []
    for i, v in enumerate(y):
        vals.append(v); wts.append(1.0); idxs.append([i])
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, i2 = vals.pop(), wts.pop(), idxs.pop()
            v1, w1, i1 = vals.pop(), wts.pop(), idxs.pop()
            vals.append((v1*w1 + v2*w2)/(w1+w2)); wts.append(w1+w2); idxs.append(i1+i2)
    fit = np.empty(len(y))
    for v, ii in zip(vals, idxs): fit[ii] = v
    return x, fit
def curve(x, y):
    """monotone curve through the centres of the PAV blocks (no flat steps
    inside the data); clamps outside the fitted range -- never extrapolates."""
    kx, ky = pav(x, y)
    cx, cy = [], []
    for v in np.unique(ky):
        sel = ky == v
        cx.append(kx[sel].mean()); cy.append(v)
    o = np.argsort(cx); cx, cy = np.asarray(cx)[o], np.asarray(cy)[o]
    cx = np.concatenate([[kx.min()], cx, [kx.max()]]); cy = np.concatenate([[cy[0]], cy, [cy[-1]]])
    return lambda q: np.interp(q, cx, cy)

def spearman(a, b): return float(pd.Series(a).rank().corr(pd.Series(b).rank()))

# ---- leave-one-out test ----
loo = []
for p in POS:
    q = pairs[pairs.pos == p].reset_index(drop=True)
    for i in range(len(q)):
        rest = q.drop(i)
        loo.append(dict(pos=p, rookie=q.rookie[i], vor=q.vor[i], pred=float(curve(rest.idx, rest.vor)(q.idx[i]))))
loo = pd.DataFrame(loo)
test = {'n_pairs': len(pairs), 'n_by_pos': pairs.pos.value_counts().to_dict(),
        'loo_spearman_all': round(spearman(loo.pred, loo.vor), 4), 'loo_mae_all': round(float((loo.pred-loo.vor).abs().mean()), 1),
        'loo_by_pos': {p: {'n': int((loo.pos == p).sum()), 'spearman': round(spearman(loo[loo.pos == p].pred, loo[loo.pos == p].vor), 4),
                           'mae': round(float((loo[loo.pos == p].pred - loo[loo.pos == p].vor).abs().mean()), 1)} for p in POS},
        'rookies_2026': {'n': int(loo.rookie.sum()), 'spearman': round(spearman(loo[loo.rookie].pred, loo[loo.rookie].vor), 4),
                         'mean_pred_minus_actual': round(float((loo[loo.rookie].pred - loo[loo.rookie].vor).mean()), 1),
                         'mae': round(float((loo[loo.rookie].pred - loo[loo.rookie].vor).abs().mean()), 1)}}
C = {p: curve(pairs[pairs.pos == p].idx, pairs[pairs.pos == p].vor) for p in POS}

# ---- devy: Week-9 re-ordering of the Week-7 index ----
w9 = json.load(open(W09))
rank9 = {}
for p in POS:
    for r in w9['data'][p]['rows']:
        rank9['cfbd:%s' % r['id']] = (p, r['rank'], r['name'], r['team'], r.get('status'), r.get('yoh'))
dev = []
for a in A:
    if a['population'] != 'devy': continue
    idx, st, reason = fv(a)
    dev.append(dict(id=a['id'], name=a['name'], pos=a['position'], team=a.get('team'), idx7=idx, status=st, reason=reason,
                    ord7=a.get('canonical_devy_ordinal')))
dev = pd.DataFrame(dev)
dev['in_w9'] = dev.id.isin(rank9)
dev['rank9'] = dev.id.map(lambda i: rank9[i][1] if i in rank9 else np.nan)
dev['yoh'] = dev.id.map(lambda i: rank9[i][5] if i in rank9 else np.nan)
dev['idx9'] = dev.idx7
for p in POS:
    m = (dev.pos == p) & dev.idx7.notna() & dev.in_w9
    vals = np.sort(dev.loc[m, 'idx7'].values)[::-1]
    order = dev.loc[m].sort_values('rank9').index
    dev.loc[order, 'idx9'] = vals
dev['vor_value'] = [float(C[p](v)) if pd.notna(v) else np.nan for p, v in zip(dev.pos, dev.idx9)]
dev['priced'] = dev.vor_value.notna()
# Above the feed's anchor support (e.g. Jeremiah Smith): stay unpriced (no
# extrapolation), but carry an honest floor = the highest priced devy value at
# the position, so tools can show ">= floor" instead of nothing.
top_dev = dev[dev.priced].groupby('pos').vor_value.max()
dev['floor_value'] = np.where(dev.reason == 'ABOVE_ANCHOR_SUPPORT', dev.pos.map(top_dev), np.nan)

# ---- unified file ----
nfl = pd.read_csv(NFLVOR)
uni = pd.concat([
    pd.DataFrame({'population': 'nfl', 'id': nfl.pid, 'sleeper_id': nfl.sleeper_id, 'name': nfl.name, 'pos': nfl.pos, 'team': nfl.team,
                  'priced': nfl.priced, 'unpriced_reason': np.where(nfl.priced, '', 'ROSTER_STATUS_' + nfl.status.astype(str)),
                  'vor_value': nfl.vor_value.where(nfl.priced).round(1), 'floor_value': np.nan, 'source': 'claude_nfl_vor_v1_w08'}),
    pd.DataFrame({'population': 'devy', 'id': dev.id, 'sleeper_id': '', 'name': dev.name, 'pos': dev.pos, 'team': dev.team,
                  'priced': dev.priced, 'unpriced_reason': np.where(dev.priced, '', dev.reason.fillna('FEED_UNPRICED')),
                  'vor_value': dev.vor_value.round(1), 'floor_value': dev.floor_value.round(1), 'source': np.where(dev.in_w9, 'v86w_w09_order__feed_w07_index__bridge', 'v86w_w07_feed_index__bridge')})],
    ignore_index=True)
uni['rank'] = uni.vor_value.rank(ascending=False, method='first')
uni = uni.sort_values('vor_value', ascending=False, na_position='last')
uni.to_csv(f'{OUT}/au_vor_values_{TAG}.csv', index=False)
json.dump(test, open(f'{OUT}/bridge_test_{TAG}.json', 'w'), indent=1)
print(json.dumps(test, indent=1))
print('devy priced', int(dev.priced.sum()), 'of', len(dev), '| in w9', int(dev.in_w9.sum()))
top = uni[uni.priced].head(40)
print('\nTOP 40 combined:', '; '.join(f"{r.name} {r.pos} {r.population[0].upper()} {r.vor_value:.0f}" for r in top.itertuples()))
print('\nABOVE SUPPORT (unpriced, floor):', uni[uni.floor_value.notna()][['name', 'pos', 'floor_value']].to_string(index=False))
print('distinct devy values among priced:', uni[(uni.population == 'devy') & uni.priced].vor_value.nunique(), 'of', int(((uni.population == 'devy') & uni.priced).sum()))
d = uni[(uni.population == 'devy') & uni.priced].head(15)
print('\nTOP 15 devy:', '; '.join(f"{r.name} {r.pos} {r.team} {r.vor_value:.0f}" for r in d.itertuples()))
