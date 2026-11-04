import sys
S='/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
sys.argv=['x',S+'/nfl',S+'/review_vor/extra_starter']
sys.path.insert(0,'/home/user/devydose-board/modeling/vor_v1/code')
import numpy as np, pandas as pd
import vor_nfl as V
def sp(a,b): return float(np.corrcoef(pd.Series(a).rank(),pd.Series(b).rank())[0,1])
comp=V.rows[V.rows.H_complete]; tr=comp[comp.y+2<2018]; ts=comp[comp.y.between(2018,2023)].copy()
def go():
    p,_=V.predict(ts,V.fit(tr,True),True); return np.abs(p-ts.H).mean(), sp(p,ts.H)
print('default SIG', {k:tuple(round(x,3) for x in v) for k,v in V.SIG.items()}, go())
pm=V.W[V.W.y<=2017].groupby(['pid','y','pos']).pts.agg(['mean','std','size']).reset_index(); pm=pm[pm['size']>=6]
for p in V.POS:
    q=pm[pm.pos==p]; b,a=np.polyfit(q['mean'],q['std'],1); V.SIG[p]=(float(a),float(b))
print('train-only SIG', {k:tuple(round(x,3) for x in v) for k,v in V.SIG.items()}, go())
