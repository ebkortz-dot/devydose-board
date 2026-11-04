import pandas as pd, json, sys
from collections import defaultdict
D=sys.argv[1]
live=json.load(open(f'{D}/pro_values_live.json'))['players']
pl=pd.read_csv(f'{D}/players.csv',low_memory=False)
w=pd.read_pickle(sys.argv[2])
idx=defaultdict(list)
for r in pl.itertuples():
    if isinstance(r.display_name,str) and isinstance(r.gsis_id,str): idx[(r.display_name,r.position)].append(r.gsis_id)
pli=pl.drop_duplicates('gsis_id').set_index('gsis_id')
t26=w[w.season==2026].groupby('player_id').team.last()
t25=w[w.season==2025].groupby('player_id').team.last()
TEAMFIX={'AZ':'ARI','LAR':'LA','JAC':'JAX','WSH':'WAS'}
bad=[]
for p in live:
    g=p.get('gsis_id'); how='board'
    if not g:
        ids=idx.get((p['name'],p['pos']),[]); how='name'
        if len(ids)!=1:
            print('NOMATCH',p['name'],p['pos'],p.get('team'),p['val'],len(ids), 'name-any-pos:',[(k[1],v) for k,v in idx.items() if k[0]==p['name']][:3]); continue
        g=ids[0]
    nm=pli.display_name.get(g); ps=pli.position.get(g)
    bt=TEAMFIX.get(p.get('team'),p.get('team'))
    tm=t26.get(g, None)
    if nm!=p['name'] or ps!=p['pos'] or (tm is not None and tm!=bt):
        bad.append((how,p['name'],p['pos'],p.get('team'),p['val'],g,nm,ps,tm,t25.get(g),pli.rookie_season.get(g),pli.draft_pick.get(g)))
for b in bad: print('CHK',b)
# board gsis duplicates
from collections import Counter
c=Counter(p.get('gsis_id') for p in live if p.get('gsis_id')); print('dup gsis on board',[k for k,v in c.items() if v>1])
c=Counter((p['name'],p['pos']) for p in live); print('dup name on board',[k for k,v in c.items() if v>1])
