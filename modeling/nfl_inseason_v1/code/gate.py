"""In-season NFL value refresh -- GATE.

Question: once a season is N weeks old, does blending a player's in-season
points-per-game into his prior expectation predict his FUTURE production
better than the prior alone?

  prior  = previous-season PPG (>=4 games). Players with no prior season use the
           position's rookie-year mean PPG from the training seasons.
  early  = PPG over weeks 1..N of the season (>=1 game).
  blend  = (k*prior + g*early) / (k + g),  g = games played in weeks 1..N,
           k = shrink in games, chosen on the training seasons only.
  Targets (both must improve):
    T1 rest-of-season PPG, weeks N+1..18 (>=3 games)
    T2 next-season PPG (>=4 games)
Scoring: full PPR, 4-pt... no: 6-pt passing TD (AU format), -2 INT, -2 fumble lost.
Paired worst-of-two-splits: delta computed WITHIN each split, then the worse one.
"""
import csv, json, sys, math, statistics as st
from collections import defaultdict

D = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
POS = ('QB', 'RB', 'WR', 'TE')

def f(x):
    try: return float(x)
    except: return 0.0

def fpts(r):
    return (f(r['passing_yards'])*0.04 + f(r['passing_tds'])*6 - f(r['passing_interceptions'])*2
            + f(r['rushing_yards'])*0.1 + f(r['rushing_tds'])*6
            + f(r['receptions'])*1 + f(r['receiving_yards'])*0.1 + f(r['receiving_tds'])*6
            + (f(r['passing_2pt_conversions'])+f(r['rushing_2pt_conversions'])+f(r['receiving_2pt_conversions']))*2
            - (f(r['sack_fumbles_lost'])+f(r['rushing_fumbles_lost'])+f(r['receiving_fumbles_lost']))*2)

def load(y):
    """player -> list of (week, pts), regular season only; plus position."""
    g, pos = defaultdict(list), {}
    for r in csv.DictReader(open(f'{D}/stats_{y}.csv')):
        if r['season_type'] != 'REG' or r['position'] not in POS: continue
        g[r['player_id']].append((int(r['week']), fpts(r)))
        pos[r['player_id']] = r['position']
    return g, pos

def ppg(lst, lo=1, hi=99):
    x = [p for w, p in lst if lo <= w <= hi]
    return (sum(x)/len(x), len(x)) if x else (None, 0)

if __name__ == '__main__':
    years = list(range(2012, 2026))
    S = {y: load(y) for y in years}
    rows = []
    for y in range(2013, 2026):
        g, pos = S[y]; gp, _ = S[y-1]; gn = S[y+1][0] if y+1 in S else {}
        for pid, lst in g.items():
            e, ge = ppg(lst, 1, N)
            if ge < 1: continue
            pr, gpr = ppg(gp.get(pid, []))
            t1, g1 = ppg(lst, N+1, 18)
            t2, g2 = ppg(gn.get(pid, [])) if gn else (None, 0)
            rows.append(dict(y=y, pid=pid, pos=pos[pid], early=e, ge=ge,
                             prior=pr if gpr >= 4 else None,
                             t1=t1 if g1 >= 3 else None, t2=t2 if g2 >= 4 else None))
    json.dump(rows, open(f'{D}/gate_rows_N{N}.json', 'w'))

    def rookie_mean(train):
        m = {}
        for p in POS:
            # first-season PPG of players with no prior season (any games), from training seasons
            x = [r['early'] for r in train if r['pos'] == p and r['prior'] is None]
            m[p] = st.mean(x) if x else 0
        return m

    def predict(r, k, rm):
        pr = r['prior'] if r['prior'] is not None else rm[r['pos']]
        return pr, (k*pr + r['ge']*r['early']) / (k + r['ge'])

    def mae(rs, k, rm, t):
        a = [abs(predict(r, k, rm)[1] - r[t]) for r in rs if r[t] is not None]
        b = [abs(predict(r, k, rm)[0] - r[t]) for r in rs if r[t] is not None]
        return (st.mean(a), st.mean(b), len(a)) if a else (None, None, 0)

    def spearman(xs, ys):
        def rk(v):
            o = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
            for i, j in enumerate(o): r[j] = i
            return r
        a, b = rk(xs), rk(ys); n = len(a)
        return 1 - 6*sum((a[i]-b[i])**2 for i in range(n)) / (n*(n*n-1))

    splits = {'A: train 2013-18 -> test 2019-25': (range(2013, 2019), range(2019, 2026)),
              'B: train 2019-25 -> test 2013-18': (range(2019, 2026), range(2013, 2019))}
    K = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 30]
    report = {'N': N, 'splits': {}}
    for name, (tr, te) in splits.items():
        trn = [r for r in rows if r['y'] in tr]; tst = [r for r in rows if r['y'] in te]
        rm = rookie_mean(trn)
        # k chosen on TRAIN, on the mean of both targets' MAE
        def obj(k): return sum(mae(trn, k, rm, t)[0] for t in ('t1', 't2'))
        k = min(K, key=obj)
        out = {'k': k, 'rookie_mean': {p: round(v, 2) for p, v in rm.items()}}
        for t in ('t1', 't2'):
            for grp, sel in [('all', lambda r: True)] + [(p, (lambda p: lambda r: r['pos'] == p)(p)) for p in POS] + \
                            [('vets', lambda r: r['prior'] is not None), ('no_prior', lambda r: r['prior'] is None)]:
                rs = [r for r in tst if sel(r) and r[t] is not None]
                if len(rs) < 5: continue
                mb, mp, n = mae(rs, k, rm, t)
                pb = [predict(r, k, rm)[1] for r in rs]; pp = [predict(r, k, rm)[0] for r in rs]; tt = [r[t] for r in rs]
                out[f'{t}/{grp}'] = dict(n=n, mae_prior=round(mp, 3), mae_blend=round(mb, 3), d_mae=round(mb-mp, 3),
                                         rho_prior=round(spearman(pp, tt), 4), rho_blend=round(spearman(pb, tt), 4),
                                         d_rho=round(spearman(pb, tt)-spearman(pp, tt), 4))
        report['splits'][name] = out
    # worst-of-two-splits per cell
    worst = {}
    cells = set(k for s in report['splits'].values() for k in s if '/' in k)
    for c in sorted(cells):
        ds = [s[c] for s in report['splits'].values() if c in s]
        if len(ds) == 2:
            worst[c] = dict(worst_d_mae=max(d['d_mae'] for d in ds), worst_d_rho=min(d['d_rho'] for d in ds),
                            n=[d['n'] for d in ds])
    report['worst_of_two'] = worst
    json.dump(report, open(f'{D}/gate_report_N{N}.json', 'w'), indent=1)
    for name, s in report['splits'].items():
        print(name, 'k =', s['k'])
    print(f"{'cell':16} {'worst dMAE':>10} {'worst dRho':>10}  n(A,B)")
    for c, w in worst.items():
        print(f"{c:16} {w['worst_d_mae']:>10} {w['worst_d_rho']:>10}  {w['n']}")
