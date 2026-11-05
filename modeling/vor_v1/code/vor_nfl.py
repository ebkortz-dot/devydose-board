"""Claude VOR model, NFL side (v1).

Currency: expected WEEKLY value over replacement, summed over a horizon.
  League (Erik, 2026-11-04): 12 teams, superflex, full PPR, 6-pt pass TD,
  lineup QB / 2RB / 3WR / TE / 2 FLEX(RB/WR/TE) / SF(QB/RB/WR/TE).
  Weekly VOR = max(0, points - R_pos). Horizon = rest of season y (weeks 9-18)
  + season y+1 + season y+2, undiscounted (POLICY).
Replacement R_pos (derived, not fitted): each season, fill 12 lineups greedily by
season PPG (min 6 games) -- QB12, RB24, WR36, TE12, then FLEX24 best remaining
RB/WR/TE, then SF12 best remaining of all four; R_pos = PPG of the best
non-starter at the position. Averaged over 2013-2025.

Prediction at the end of Week 8 of season y, per position:
  PPG in each window t (ROS, Y1, Y2): linear model on
    prior_eff, prior2_eff, early*g/(g+3), g/(g+3), age, age^2, noprior
  games in each window: linear model on the same + prior-season games, clipped.
  weekly sd: sigma = a + b*mu per position (from weekly data).
  E[weekly VOR] = E[max(0, X - R)], X ~ Normal(mu, sigma)  (closed form).
  Predicted H = sum_t E[games_t] * E[weekly VOR_t].
prior_eff = previous-season PPG (>=4 g) else a draft-capital prior
(PPG ~ a + b*log(pick), training rows only); prior2_eff = two seasons back
(>=4 g) else prior_eff.
Gate: realized H vs predicted, MAE + tie-averaged Spearman, two paired splits,
worst of two, against (b0) the same machinery WITHOUT in-season information and
(b1) naive 2.5 x previous-season VOR. Split A purges training rows whose target
window reaches into the test seasons.
"""
import sys, json, math, csv
import numpy as np, pandas as pd

D = sys.argv[1]; OUT = sys.argv[2]
N = 8
POS = ['QB', 'RB', 'WR', 'TE']
LINEUP = {'QB': 12, 'RB': 24, 'WR': 36, 'TE': 12}
FLEX, SF = 24, 12
import os
# POLICY (Erik's call): 'starter' = replacement is the best non-starter (value over
# last starter); 'waiver' = replacement is the player at rank 1.5 x starters + 1,
# i.e. roughly the best player still on waivers once benches are filled.
REPL_MODE = os.environ.get('VOR_REPL', 'starter')
QB_REPL_RANK = int(os.environ.get('VOR_QB_RANK', 36))   # Erik 2026-11-05: QB36 (QB30 tested, too deflated)

def fpts(df):
    g = lambda c: pd.to_numeric(df[c], errors='coerce').fillna(0)
    return (g('passing_yards')*0.04 + g('passing_tds')*6 - g('passing_interceptions')*2
            + g('rushing_yards')*0.1 + g('rushing_tds')*6 + g('receptions') + g('receiving_yards')*0.1 + g('receiving_tds')*6
            + (g('passing_2pt_conversions')+g('rushing_2pt_conversions')+g('receiving_2pt_conversions'))*2
            - (g('sack_fumbles_lost')+g('rushing_fumbles_lost')+g('receiving_fumbles_lost'))*2)

# v4 position resolution (review: Travis Hunter is listed CB in nflverse stats):
# keep the stats position when it is QB/RB/WR/TE; otherwise use the player's
# 2026 team-roster position if that is QB/RB/WR/TE; FB counts as RB; anything
# else (DB, punters, DL with a gadget carry) is dropped.
_rp = pd.read_csv(f'{D}/roster_weekly_2026.csv', low_memory=False).sort_values('week').groupby('gsis_id').position.last()
def resolve_pos(pid, pos):
    if pos in POS: return pos
    rp = _rp.get(pid)
    if rp in POS: return rp
    return 'RB' if pos == 'FB' else None
frames = []
for y in range(2012, 2027):
    df = pd.read_csv(f'{D}/stats_{y}.csv', low_memory=False)
    df = df[df.season_type == 'REG'].copy()
    df['rpos'] = [resolve_pos(a, b) for a, b in zip(df.player_id, df.position)]
    df = df[df.rpos.notna()]
    frames.append(pd.DataFrame({'pid': df.player_id, 'y': y, 'w': df.week.astype(int), 'pos': df.rpos, 'pts': fpts(df)}))
W = pd.concat(frames, ignore_index=True)
assert not W.duplicated(['pid', 'y', 'w']).any()

# ---- replacement levels ----
def repl_season(y):
    s = W[W.y == y].groupby(['pid', 'pos']).pts.agg(['mean', 'size']).reset_index()
    s = s[s['size'] >= 6].sort_values('mean', ascending=False)
    starters = set()
    for p in POS: starters |= set(s[s.pos == p].pid.head(LINEUP[p]))
    rest = s[~s.pid.isin(starters)]
    starters |= set(rest[rest.pos.isin(['RB', 'WR', 'TE'])].pid.head(FLEX))
    rest = s[~s.pid.isin(starters)]
    starters |= set(rest.pid.head(SF))
    out = {}
    for p in POS:
        n_st = int(((s.pos == p) & s.pid.isin(starters)).sum())
        if REPL_MODE == 'waiver':
            # Erik 2026-11-04: QB replacement = QB30; RB/WR/TE = rank 1.5 x starters + 1
            k = QB_REPL_RANK if p == 'QB' else int(math.ceil(1.5*n_st)) + 1
            out[p] = float(s[s.pos == p]['mean'].iloc[k - 1])
        else:
            nb = s[(s.pos == p) & ~s.pid.isin(starters)]
            out[p] = float(nb['mean'].iloc[0])
        out[p + '_starters'] = n_st
    return out
RS = {y: repl_season(y) for y in range(2013, 2026)}
R = {p: float(np.mean([RS[y][p] for y in RS])) for p in POS}
W['vor'] = np.maximum(0, W.pts - W.pos.map(R))
# Baseline (v2, review finding 1): a replacement-level player still banks his
# good weeks under max(0, pts-R). B_pos = mean weekly VOR of real seasons with
# >=14 games and PPG within R +/- 0.5 (2013-2025). Value is measured ABOVE it,
# so a replacement-level player is worth ~0 and values are additive.
_s = W[W.y.between(2013, 2025)].groupby(['pid', 'y', 'pos']).agg(g=('pts', 'size'), ppg=('pts', 'mean'), v=('vor', 'mean')).reset_index()
B = {p: float(_s[(_s.pos == p) & (_s.g >= 14) & ((_s.ppg - R[p]).abs() <= 0.5)].v.mean()) for p in POS}
B_n = {p: int(((_s.pos == p) & (_s.g >= 14) & ((_s.ppg - R[p]).abs() <= 0.5)).sum()) for p in POS}

# ---- explicit age gates (Erik, 2026-11-04) ----
# POLICY with data-derived knots: among seasons with >=8 games above replacement
# (2013-2025), full value through the position's 90th-percentile age, a linear
# taper to zero at the 97.5th percentile, zero beyond. Applied to the y+1 and
# y+2 windows (the rest of the current season is not gated: he is playing now).
_sa = W[W.y.between(2013, 2025)].groupby(['pid', 'y', 'pos']).agg(g=('pts', 'size'), ppg=('pts', 'mean')).reset_index()
_bd = pd.read_csv(f'{D}/players.csv', low_memory=False, usecols=['gsis_id', 'birth_date']).drop_duplicates('gsis_id').set_index('gsis_id').birth_date
_bd = pd.to_datetime(_bd, errors='coerce')
_sa['age'] = [(pd.Timestamp(f'{y}-09-01') - _bd.get(p_, pd.NaT)).days/365.25 if pd.notna(_bd.get(p_, pd.NaT)) else np.nan for p_, y in zip(_sa.pid, _sa.y)]
_good = _sa[(_sa.g >= 8) & (_sa.ppg > _sa.pos.map(R))]
AGE_GATE = {p: (float(np.percentile(_good[_good.pos == p].age.dropna(), 90)), float(np.percentile(_good[_good.pos == p].age.dropna(), 97.5))) for p in POS}
# Erik 2026-11-04: more conservative curve -- QB knots two years later, the others one year later
AGE_SHIFT = {'QB': 2.0, 'RB': 1.0, 'WR': 1.0, 'TE': 1.0}
AGE_GATE = {p: (lo + AGE_SHIFT[p], hi + AGE_SHIFT[p]) for p, (lo, hi) in AGE_GATE.items()}
def age_mult(age, p):
    lo, hi = AGE_GATE[p]
    return np.clip((hi - age) / (hi - lo), 0.0, 1.0)

# ---- weekly sd vs mean, per position ----
pm = W[W.y <= 2025].groupby(['pid', 'y', 'pos']).pts.agg(['mean', 'std', 'size']).reset_index()
pm = pm[pm['size'] >= 6]
SIG = {}
for p in POS:
    q = pm[pm.pos == p]
    b, a = np.polyfit(q['mean'], q['std'], 1)
    SIG[p] = (float(a), float(b))

def ev_pos(mu, sigma, r):
    sigma = np.maximum(sigma, 0.5)
    z = (mu - r) / sigma
    pdf = np.exp(-0.5*z*z) / math.sqrt(2*math.pi)
    cdf = 0.5*(1 + np.vectorize(math.erf)(z / math.sqrt(2)))
    return sigma*pdf + (mu - r)*cdf

# ---- player metadata ----
P = pd.read_csv(f'{D}/players.csv', low_memory=False, usecols=['gsis_id', 'display_name', 'birth_date', 'draft_pick', 'position'])
P = P.drop_duplicates('gsis_id').set_index('gsis_id')
pick = pd.to_numeric(P.draft_pick, errors='coerce').fillna(260.0)
bd = pd.to_datetime(P.birth_date, errors='coerce')

# ---- rows ----
G = W.groupby(['pid', 'y'])
season = G.agg(games=('pts', 'size'), ppg=('pts', 'mean'), vor=('vor', 'sum')).reset_index()
SE = season.set_index(['pid', 'y'])
early = W[W.w <= N].groupby(['pid', 'y']).agg(ge=('pts', 'size'), early=('pts', 'mean')).reset_index()
ros = W[W.w > N].groupby(['pid', 'y']).agg(g_ros=('pts', 'size'), ppg_ros=('pts', 'mean'), vor_ros=('vor', 'sum')).reset_index()
posy = W.groupby(['pid', 'y']).pos.agg(lambda s: s.mode().iloc[0]).reset_index()
rows = early.merge(posy, on=['pid', 'y']).merge(ros, on=['pid', 'y'], how='left')
# v4 (review finding 2): add players with NO games in weeks 1..N, so the model is
# trained and gated on them: (a) veterans with >=1 game the previous season,
# (b) players drafted that year (players.csv draft_year == y).
_dy = pd.read_csv(f'{D}/players.csv', low_memory=False, usecols=['gsis_id', 'draft_year', 'position']).drop_duplicates('gsis_id').set_index('gsis_id')
_have = set(zip(rows.pid, rows.y))
_lastpos = W.groupby('pid').pos.agg(lambda s_: s_.mode().iloc[0])
_z = []
for y in range(2013, 2027):
    prev = set(W[W.y == y-1].pid)
    drafted = set(_dy.index[(_dy.draft_year == y) & (_dy.position.isin(POS))])
    for p_ in (prev | drafted):
        if (p_, y) in _have: continue
        pos_ = _lastpos.get(p_, _dy.position.get(p_))
        if pos_ not in POS: continue
        _z.append({'pid': p_, 'y': y, 'ge': 0, 'early': 0.0, 'pos': pos_})
_z = pd.DataFrame(_z).merge(ros, on=['pid', 'y'], how='left')
rows = pd.concat([rows, _z], ignore_index=True)
rows = rows[rows.y >= 2013]
def lookup(pid, y, col):
    try:
        r = SE.loc[(pid, y)]
        return r[col], r['games']
    except KeyError:
        return np.nan, 0
for lag, nm in [(1, 'prior'), (2, 'prior2')]:
    v = [lookup(p, y-lag, 'ppg') for p, y in zip(rows.pid, rows.y)]
    rows[nm] = [a if g >= 4 else np.nan for a, g in v]
    rows[nm + '_g'] = [g for a, g in v]
for k, nm in [(1, 'y1'), (2, 'y2')]:
    v = [lookup(p, y+k, 'ppg') for p, y in zip(rows.pid, rows.y)]
    rows['ppg_' + nm] = [a for a, g in v]; rows['g_' + nm] = [g for a, g in v]
    rows['vor_' + nm] = [SE.loc[(p, y+k)]['vor'] if (p, y+k) in SE.index else 0.0 for p, y in zip(rows.pid, rows.y)]
rows[['g_ros', 'vor_ros']] = rows[['g_ros', 'vor_ros']].fillna(0)
rows['H_raw'] = rows.vor_ros + rows.vor_y1 + rows.vor_y2
rows['H'] = rows.H_raw - rows.pos.map(B) * (rows.g_ros + rows.g_y1 + rows.g_y2)
rows['H_complete'] = rows.y + 2 <= 2025
rows['lpick'] = np.log(rows.pid.map(pick).fillna(260.0))
rows['age'] = [(pd.Timestamp(f'{y}-09-01') - bd.get(p, pd.NaT)).days/365.25 if pd.notna(bd.get(p, pd.NaT)) else np.nan for p, y in zip(rows.pid, rows.y)]
rows['age'] = rows.groupby('pos').age.transform(lambda s: s.fillna(s.median()))
rows['naive'] = [2.5*SE.loc[(p, y-1)]['vor'] if (p, y-1) in SE.index else 0.0 for p, y in zip(rows.pid, rows.y)]

# ---- model ----
def feats(df, dp, use_inseason=True):
    pr = df.prior.copy(); nop = pr.isna()
    pr[nop] = (dp[0] + dp[1]*df.lpick)[nop]
    pr = pr.clip(lower=0.5)
    pr2 = df.prior2.fillna(pr)
    g = df['ge']
    cols = [np.ones(len(df)), pr, pr2, df.age, df.age**2, nop.astype(float), df.prior_g]
    if use_inseason: cols += [df.early*g/(g+3), g/(g+3)]
    return np.column_stack(cols)

def fit_lin(X, y, ridge=1e-3):
    A = X.T @ X + ridge*np.eye(X.shape[1]); A[0, 0] -= ridge
    return np.linalg.solve(A, X.T @ y)

def pav_curve(x, y):
    o = np.argsort(x); x, y = np.asarray(x, float)[o], np.asarray(y, float)[o]
    vals, wts, idxs = [], [], []
    for i, v in enumerate(y):
        vals.append(v); wts.append(1.0); idxs.append([i])
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, i2 = vals.pop(), wts.pop(), idxs.pop(); v1, w1, i1 = vals.pop(), wts.pop(), idxs.pop()
            vals.append((v1*w1 + v2*w2)/(w1 + w2)); wts.append(w1 + w2); idxs.append(i1 + i2)
    cx = np.array([x[ii].mean() for ii in idxs]); cy = np.array(vals)
    return cx, cy   # v4: block centres only; above the last centre predict() continues proportionally

def fit(train, use_inseason):
    """v2: linear core + per-position isotonic recalibration fitted on
    leave-one-season-out predictions within the training rows only."""
    M = fit_core(train, use_inseason)
    tr = train[train.H_complete].copy()
    oof = np.full(len(tr), np.nan)
    for s_ in sorted(tr.y.unique()):
        ix = (tr.y == s_).values
        Ms = fit_core(train[train.y != s_], use_inseason)
        oof[ix], _ = predict(tr[ix], Ms, use_inseason, scaled=False)
    for p in POS:
        ix = (tr.pos == p).values
        M[p]['iso'] = pav_curve(oof[ix], tr.H.values[ix])
    return M

def fit_core(train, use_inseason):
    M = {}
    for p in POS:
        t = train[train.pos == p]
        npr = t[t.prior.isna() & (t['ge'] > 0)]   # zero-game rows carry no early PPG
        tgt = npr.ppg_ros.fillna(npr.early)
        b, a = np.polyfit(npr.lpick, tgt, 1)
        dp = (a, b); m = {'dp': dp}
        X = feats(t, dp, use_inseason)
        for w, pc, gc, mx in [('ros', 'ppg_ros', 'g_ros', 10), ('y1', 'ppg_y1', 'g_y1', 17), ('y2', 'ppg_y2', 'g_y2', 17)]:
            ok = (t[gc] >= 3).values
            m[w + '_ppg'] = fit_lin(X[ok], t[pc].values[ok])
            m[w + '_s'] = float(np.std(t[pc].values[ok] - X[ok] @ m[w + '_ppg']))
            m[w + '_g'] = fit_lin(X, t[gc].values.astype(float))
            m[w + '_max'] = mx
        M[p] = m
    return M

def predict(df, M, use_inseason, scaled=True):
    out = np.zeros(len(df)); parts = {}
    for p in POS:
        ix = (df.pos == p).values
        if not ix.any(): continue
        m = M[p]; X = feats(df[ix], m['dp'], use_inseason)
        a, b = SIG[p]; tot = np.zeros(ix.sum())
        for w in ('ros', 'y1', 'y2'):
            mu = np.clip(X @ m[w + '_ppg'], 0, None)
            g = np.clip(X @ m[w + '_g'], 0, m[w + '_max'])
            # weekly noise plus uncertainty in the projection itself
            sig = np.sqrt((a + b*mu)**2 + m[w + '_s']**2)
            v = g * (ev_pos(mu, sig, R[p]) - B[p])
            if w != 'ros':
                v = v * age_mult(df[ix].age.values + (1 if w == 'y1' else 2), p)
            tot += v; parts.setdefault(w, np.zeros(len(df)))[ix] = v
            parts.setdefault(w + '_mu', np.zeros(len(df)))[ix] = mu
            parts.setdefault(w + '_g', np.zeros(len(df)))[ix] = g
        if scaled and 'iso' in m:
            cx, cy = m['iso']
            cal = np.interp(tot, cx, cy)
            top = tot > cx[-1]   # v4: continue proportionally above the top knot (no flat cap)
            if cx[-1] > 0: cal[top] = cy[-1] * tot[top] / cx[-1]
            out[ix] = cal
        else:
            out[ix] = tot
    return out, parts

def waiver_rank(p):
    if p == 'QB' and REPL_MODE == 'waiver': return QB_REPL_RANK
    return int(math.ceil(1.5 * RS[2025][p + '_starters'])) + 1
def recentre(df, col, by=('y',)):
    """v4 (review finding 3): subtract, per season and position, the value of the
    player at the position's waiver rank, so the freely available player is worth 0
    at every position (cross-position additivity)."""
    out = df[col].copy()
    for keys, g in df.groupby(list(by) + ['pos']):
        p = keys[-1]; k = waiver_rank(p)
        q = g[col].sort_values(ascending=False)
        ref = q.iloc[k-1] if len(q) >= k else 0.0
        out.loc[g.index] = g[col] - ref
    return out

def rank(v):
    return pd.Series(v).rank(method='average').values
def spearman(x, y):
    return float(np.corrcoef(rank(x), rank(y))[0, 1])

if __name__ == '__main__':
    comp = rows[rows.H_complete]
    splits = {'A: train 2013-17 (purged) -> test 2018-23': (lambda d: d.y + 2 < 2018, range(2018, 2024)),
              'B: train 2018-23 -> test 2013-17': (lambda d: d.y >= 2018, range(2013, 2018))}
    rep = {'R': R, 'R_by_season': RS, 'sigma': SIG, 'baseline_B': B, 'baseline_n': B_n, 'age_gate': AGE_GATE, 'splits': {}}
    for nm, (trsel, te) in splits.items():
        tr = comp[trsel(comp)]; ts = comp[comp.y.isin(te)].copy()
        M1 = fit(tr, True); M0 = fit(tr, False)
        ts['pred'], _ = predict(ts, M1, True); ts['base0'], _ = predict(ts, M0, False)
        ts['pred_rc'] = recentre(ts, 'pred'); ts['base0_rc'] = recentre(ts, 'base0'); ts['H_rc'] = recentre(ts, 'H')
        res = {}
        for grp in ['all'] + POS + ['vets', 'no_prior', 'zero_games', 'top200', 'all_recentred']:
            if grp == 'all': q = ts
            elif grp == 'vets': q = ts[ts.prior.notna()]
            elif grp == 'no_prior': q = ts[ts.prior.isna()]
            elif grp == 'zero_games': q = ts[ts['ge'] == 0]
            elif grp == 'all_recentred': q = ts
            elif grp == 'top200': q = ts[ts.pred.rank(ascending=False) <= 200*len(te)]
            else: q = ts[ts.pos == grp]
            if len(q) < 5: continue
            r = {'n': len(q)}
            if grp == 'all_recentred':
                q = ts
                for col, tgt in [('pred', 'H_rc'), ('base0', 'H_rc'), ('naive', 'H_rc')]:
                    c = col + '_rc' if col != 'naive' else 'naive'
                    r['mae_' + col] = round(float(np.mean(np.abs(q[c] - q[tgt]))), 2)
                    r['rho_' + col] = round(spearman(q[c], q[tgt]), 4)
                res[grp] = r; continue
            for col in ['pred', 'base0', 'naive']:
                r['mae_' + col] = round(float(np.mean(np.abs(q[col] - q.H))), 2)
                r['rho_' + col] = round(spearman(q[col], q.H), 4)
            res[grp] = r
        rep['splits'][nm] = res
    worst = {}
    for grp in rep['splits'][list(splits)[0]]:
        a, b = (rep['splits'][s].get(grp) for s in splits)
        if a and b:
            worst[grp] = {'n': [a['n'], b['n']],
                          'vs_base0_dMAE': max(a['mae_pred']-a['mae_base0'], b['mae_pred']-b['mae_base0']),
                          'vs_base0_dRho': min(a['rho_pred']-a['rho_base0'], b['rho_pred']-b['rho_base0']),
                          'vs_naive_dMAE': max(a['mae_pred']-a['mae_naive'], b['mae_pred']-b['mae_naive']),
                          'vs_naive_dRho': min(a['rho_pred']-a['rho_naive'], b['rho_pred']-b['rho_naive'])}
    rep['worst_of_two'] = worst
    json.dump(rep, open(f'{OUT}/vor_gate_report.json', 'w'), indent=1, default=float)
    rows.to_pickle(f'{OUT}/vor_rows.pkl')
    print('R', {k: round(v, 2) for k, v in R.items()}, 'starters/season', {p: RS[2025][p + '_starters'] for p in POS})
    for nm, res in rep['splits'].items():
        print(nm); [print('  ', g, r) for g, r in res.items()]
    print('WORST OF TWO'); [print('  ', g, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in w.items()}) for g, w in worst.items()]
