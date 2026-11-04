import sys, os
S='/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
mode=os.environ.get('VOR_REPL','starter')
sys.argv=['x',S+'/nfl',S+'/review_vor/extra_'+mode]
sys.path.insert(0,'/home/user/devydose-board/modeling/vor_v1/code')
import numpy as np, pandas as pd
import vor_nfl as V
W=V.W
s=W[W.y<=2025].groupby(['pid','y','pos']).agg(g=('pts','size'),ppg=('pts','mean'),vor=('vor','sum')).reset_index()
for p in V.POS:
    q=s[(s.pos==p)&(s.g>=14)&((s.ppg-V.R[p]).abs()<0.5)]
    print(mode,p,'R=%.2f'%V.R[p],'player-seasons at PPG=R+-0.5 (>=14g): n=%d, mean realized season VOR %.1f, per game %.2f'%(len(q),q.vor.mean(),(q.vor/q.g).mean()))
for nm in ['A','B']:
    ts=pd.read_pickle(S+f'/review_vor/gate_{mode}/ts{nm}.pkl')
    t=ts[ts.pos=='TE'].sort_values('pred',ascending=False)
    for k in (3,6,12):
        q=t.groupby('y').head(k); print(mode,nm,'TE top%d/season pred %.1f realized %.1f ratio %.2f n=%d'%(k,q.pred.mean(),q.H.mean(),q.pred.mean()/q.H.mean(),len(q)))
    # relative mispricing: top-12 overall vs players ranked 61-120
    t=ts.sort_values('pred',ascending=False); t['r']=t.groupby('y').pred.rank(ascending=False)
    a=t[t.r<=12]; b=t[(t.r>60)&(t.r<=120)]
    print(mode,nm,'ratio pred/H top12 %.2f vs ranks61-120 %.2f'%(a.pred.sum()/a.H.sum(), b.pred.sum()/b.H.sum()))
