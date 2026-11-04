"""In-season NFL value refresh -- APPLY (only after gate.py passes).

For every player in the live pro_values.json:
  prior  = 2025 PPG (>=4 games); if absent (rookies, backups), the PPG his draft
           capital implies: per position, PPG ~ a + b*log(pick), fitted on every
           no-prior player-season 2013-2025 (gate_np.py validated this prior and
           its k). Backing a prior out of the preseason VALUE was tried first and
           rejected: a rookie's dynasty premium maps to impossible PPG (Love ~60).
  blend  = (K*prior + g*early) / (K + g), early = 2026 PPG weeks 1..N, g = games.
  val'   = val * (blend / prior) ** beta_pos
beta_pos (FITTED on the live board itself): slope of log(val) on log(2025 PPG)
among veterans with >=4 games, i.e. how much dynasty value the board already
pays per unit of production at that position. The update therefore moves a
player only by what his in-season production changes, in the board's own
currency. Players with no 2026 games keep their value (no stat row is not a
zero-performance observation) and are flagged.
Identity: gsis_id where the board has it, else EXACT name + position against
nflverse players.csv (unique match only). Never fuzzy.
"""
import csv, json, math, sys, datetime as dt
from collections import defaultdict
sys.path.insert(0, sys.argv[3])
from gate import load, ppg, POS

D, N = sys.argv[1], int(sys.argv[2])
K = 3                     # chosen on training seasons in both gate splits
PPG_FLOOR = 0.5           # POLICY: guards log/ratio against ~0 PPG
# POLICY (not fitted): the ratio is taken against at least a deep-roster
# replacement level -- the 2025 PPG (>=4 games) of QB32 / RB48 / WR72 / TE24 --
# so a near-zero baseline (mop-up backups) cannot turn one start into a 10x value.
REPL_RANK = {'QB': 32, 'RB': 48, 'WR': 72, 'TE': 24}
live = json.load(open(f'{D}/pro_values_live.json'))
g25, _pos25 = load(2025); g26, pos26 = load(2026)

# exact name+pos -> gsis
idx = defaultdict(list)
for r in csv.DictReader(open(f'{D}/players.csv')):
    nm = r.get('display_name') or ''
    p = r.get('position') or ''
    if nm and r.get('gsis_id'): idx[(nm, p)].append(r['gsis_id'])
def gsis(p):
    if p.get('gsis_id'): return p['gsis_id'], 'board'
    ids = idx.get((p['name'], p['pos']), [])
    return (ids[0], 'name') if len(ids) == 1 else (None, 'unmatched' if not ids else 'ambiguous')

_byp = defaultdict(list)
for pid, lst in g25.items():
    x, n = ppg(lst)
    if n >= 4 and _pos25.get(pid) in REPL_RANK: _byp[_pos25[pid]].append(x)
REPL = {ps: sorted(v, reverse=True)[REPL_RANK[ps]-1] for ps, v in _byp.items()}

# beta per position
fitpts = defaultdict(list)
for p in live['players']:
    gid, _ = gsis(p)
    if not gid or p['val'] <= 0: continue
    pr, n = ppg(g25.get(gid, []))
    if n >= 4 and pr > PPG_FLOOR: fitpts[p['pos']].append((math.log(pr), math.log(p['val'])))
# draft-capital prior for players without a 2025 season (gate_np.py)
pick = {}
for r in csv.DictReader(open(f'{D}/players.csv')):
    try: pick[r['gsis_id']] = float(r['draft_pick']) if r['draft_pick'] else 260.0
    except: pick[r['gsis_id']] = 260.0
np_rows = [r for r in json.load(open(f'{D}/gate_rows_N{N}.json')) if r['prior'] is None]
dprior = {}
for ps in POS:
    xs = [(math.log(pick.get(r['pid'], 260.0)), r['t1'] if r['t1'] is not None else r['early']) for r in np_rows if r['pos'] == ps]
    mx = sum(x for x, _ in xs)/len(xs); my = sum(y for _, y in xs)/len(xs)
    b = sum((x-mx)*(y-my) for x, y in xs) / sum((x-mx)**2 for x, _ in xs)
    dprior[ps] = (my - b*mx, b, len(xs))
def draft_prior(gid, ps):
    a, b, _ = dprior[ps]; return max(a + b*math.log(pick.get(gid, 260.0)), PPG_FLOOR)
beta, icpt = {}, {}
for ps, pts in fitpts.items():
    mx = sum(x for x, _ in pts)/len(pts); my = sum(y for _, y in pts)/len(pts)
    b = sum((x-mx)*(y-my) for x, y in pts) / sum((x-mx)**2 for x, _ in pts)
    beta[ps], icpt[ps] = b, my - b*mx

out, audit = [], []
for p in live['players']:
    q = dict(p)
    gid, how = gsis(p)
    pr, n25 = ppg(g25.get(gid, [])) if gid else (None, 0)
    e, ge = ppg(g26.get(gid, []), 1, N) if gid else (None, 0)
    note = ''
    if not gid: note = f'id {how}'
    elif ge == 0: note = 'no 2026 games through week %d' % N
    if gid and ge > 0:
        if n25 >= 4: prior, src = max(pr, PPG_FLOOR), '2025'
        else: prior, src = draft_prior(gid, p['pos']), 'draft'
        blend = (K*prior + ge*e) / (K + ge)
        floor = REPL[p['pos']]
        mult = (max(blend, floor) / max(prior, floor)) ** beta[p['pos']]
        q['val'] = round(p['val'] * mult, 2)
        audit.append(dict(name=p['name'], pos=p['pos'], team=p.get('team'), old=p['val'], new=q['val'], mult=round(mult, 3),
                          prior_ppg=round(prior, 2), prior_src=src, ppg_2026=round(e, 2), g_2026=ge, id_via=how))
    else:
        audit.append(dict(name=p['name'], pos=p['pos'], team=p.get('team'), old=p['val'], new=p['val'], mult=1.0,
                          prior_ppg=None, prior_src=None, ppg_2026=None, g_2026=0, id_via=how, note=note))
        q['refresh_hold'] = note
    out.append(q)

out.sort(key=lambda r: -r['val'])
pr_ct = defaultdict(int)
for i, r in enumerate(out, 1):
    r['rank'] = i; pr_ct[r['pos']] += 1; r['posrank'] = pr_ct[r['pos']]
new = dict(live)
new['players'] = out
new['generated'] = dt.date.today().isoformat()
new['inseason_refresh'] = dict(
    through_week=N, season=2026, k_games=K, ppg_floor_policy=PPG_FLOOR,
    replacement_ppg_policy={k: round(v, 2) for k, v in REPL.items()}, replacement_rank_policy=REPL_RANK,
    beta_fitted={k: round(v, 3) for k, v in beta.items()}, beta_n={k: len(v) for k, v in fitpts.items()},
    draft_prior={k: dict(a=round(v[0], 3), b=round(v[1], 3), n=v[2]) for k, v in dprior.items()},
    base_generated=live['generated'],
    method='val x (blended PPG / prior PPG)^beta_pos; blend = (3*prior + g*2026 PPG)/(3+g); full PPR, 6-pt pass TD',
    note='Only `val`, `rank`, `posrank` are refreshed. Sub-fields (dynasty, win_now, adp, ...) are the preseason values.')
json.dump(new, open(f'{D}/pro_values_refreshed.json', 'w'), indent=1)
with open(f'{D}/refresh_audit.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['name','pos','team','old','new','mult','prior_ppg','prior_src','ppg_2026','g_2026','id_via','note'])
    w.writeheader(); [w.writerow(a) for a in audit]
upd = [a for a in audit if a['g_2026'] > 0]
print('replacement PPG', {k: round(v, 2) for k, v in REPL.items()})
print('beta', {k: round(v, 3) for k, v in beta.items()}, 'n', {k: len(v) for k, v in fitpts.items()})
print('updated', len(upd), 'held', len(audit)-len(upd), {h: sum(1 for a in audit if a.get('id_via')==h) for h in ('board','name','unmatched','ambiguous')})
mults = sorted(a['mult'] for a in upd)
print('mult p5/p50/p95', mults[len(mults)//20], mults[len(mults)//2], mults[-len(mults)//20])
print('TOP 15 now:', [(r['name'], r['pos'], r['val']) for r in out[:15]])
print('BIGGEST RISERS:', [(a['name'], a['old'], a['new'], a['ppg_2026'], a['g_2026']) for a in sorted(upd, key=lambda a: -(a['new']-a['old']))[:10]])
print('BIGGEST FALLERS:', [(a['name'], a['old'], a['new'], a['ppg_2026'], a['g_2026']) for a in sorted(upd, key=lambda a: (a['new']-a['old']))[:10]])
