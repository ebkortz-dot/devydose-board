"""Gate, part 2: players with NO prior season (rookies, backups with <4 games).

Prior = PPG implied by draft capital: per position, PPG ~ a + b*log(pick) fitted
on TRAINING seasons only (undrafted = pick 260). Blend weight k_np chosen on
training seasons, separately from the veterans' k. Same targets and paired
worst-of-two-splits as gate.py. Also reports a minimum-games rule.
"""
import csv, json, sys, math, statistics as st
from collections import defaultdict
D, N = sys.argv[1], int(sys.argv[2])
rows = [r for r in json.load(open(f'{D}/gate_rows_N{N}.json')) if r['prior'] is None]
pick = {}
for r in csv.DictReader(open(f'{D}/players.csv')):
    try: pick[r['gsis_id']] = float(r['draft_pick']) if r['draft_pick'] else 260.0
    except: pick[r['gsis_id']] = 260.0
for r in rows: r['lp'] = math.log(pick.get(r['pid'], 260.0))
POS = ('QB','RB','WR','TE')

def fit(train):
    m = {}
    for p in POS:
        xs = [(r['lp'], r['t1'] if r['t1'] is not None else r['early']) for r in train if r['pos']==p]
        mx = st.mean(x for x,_ in xs); my = st.mean(y for _,y in xs)
        b = sum((x-mx)*(y-my) for x,y in xs)/sum((x-mx)**2 for x,_ in xs)
        m[p] = (my-b*mx, b)
    return m
def pri(r, m): a,b = m[r['pos']]; return max(a+b*r['lp'], 0.5)
def pred(r, m, k): return (k*pri(r,m) + r['ge']*r['early'])/(k+r['ge'])
def rho(x, y):
    def rk(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); q=[0]*len(v)
        for i,j in enumerate(o): q[j]=i
        return q
    a,b = rk(x), rk(y); n=len(a)
    return 1-6*sum((a[i]-b[i])**2 for i in range(n))/(n*(n*n-1))
K = [1,2,3,4,6,8,10,12,16,20,30,50]
splits = {'A': (range(2013,2019), range(2019,2026)), 'B': (range(2019,2026), range(2013,2019))}
res = {}
for nm,(tr,te) in splits.items():
    trn=[r for r in rows if r['y'] in tr]; tst=[r for r in rows if r['y'] in te]
    m = fit(trn)
    obj = lambda k: sum(st.mean(abs(pred(r,m,k)-r[t]) for r in trn if r[t] is not None) for t in ('t1','t2'))
    k = min(K, key=obj)
    out={'k':k}
    for t in ('t1','t2'):
        for g in ('all',)+POS:
            rs=[r for r in tst if r[t] is not None and (g=='all' or r['pos']==g)]
            pb=[pred(r,m,k) for r in rs]; pp=[pri(r,m) for r in rs]; tt=[r[t] for r in rs]
            out[f'{t}/{g}']=dict(n=len(rs), d_mae=round(st.mean(abs(a-b) for a,b in zip(pb,tt))-st.mean(abs(a-b) for a,b in zip(pp,tt)),3),
                                 d_rho=round(rho(pb,tt)-rho(pp,tt),4))
    res[nm]=out
print('k_np A =',res['A']['k'],' B =',res['B']['k'])
for c in [c for c in res['A'] if '/' in c]:
    print(f"{c:9} worst dMAE {max(res[s][c]['d_mae'] for s in 'AB'):>7}  worst dRho {min(res[s][c]['d_rho'] for s in 'AB'):>7}  n {[res[s][c]['n'] for s in 'AB']}")
json.dump(res, open(f'{D}/gate_np_report_N{N}.json','w'), indent=1)
