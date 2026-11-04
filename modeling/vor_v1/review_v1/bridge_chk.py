import json, sys, numpy as np, pandas as pd
S='/tmp/claude-0/-home-user-devydose-board/b38d260e-257c-514a-9039-5459ca081318/scratchpad'
mode=sys.argv[1]
f=json.load(open(S+'/live/anchor.json')); A=f['assets']
nv=pd.read_csv(S+f'/review_vor/rerun_{mode}/nfl_vor_2026_w08.csv').set_index('pid')
def fv(a):
    v=a['values'].get('ppr6_te0',{}); return v.get('value') if v.get('status')=='priced' else None
pairs=[]; nfl_feed=[]
for a in A:
    if a['population']!='nfl': continue
    i=fv(a); nfl_feed.append(dict(pid=a['id'],name=a['name'],pos=a['position'],idx=i,st=a['values'].get('ppr6_te0',{}).get('status'),reason=a['values'].get('ppr6_te0',{}).get('reason'), rookie=a.get('rookie_season')))
    if i is None or a['id'] not in nv.index or not nv.loc[a['id']].priced: continue
    pairs.append(dict(pid=a['id'],name=a['name'],pos=a['position'],idx=i,vor=nv.loc[a['id']].vor_value,rookie=a.get('rookie_season')==2026))
P=pd.DataFrame(pairs); NF=pd.DataFrame(nfl_feed)
print('feed nfl assets',len(NF),'priced in feed',NF.idx.notna().sum(),'pairs',len(P))
print('feed NFL priced but not priced in VOR:', len(NF[NF.idx.notna() & ~NF.pid.isin(P.pid)]))
x=NF[NF.idx.notna() & ~NF.pid.isin(P.pid)].copy(); x['in_vor']=x.pid.isin(nv.index); x['vor_status']=x.pid.map(nv.status)
print(x.sort_values('idx',ascending=False).head(15)[['name','pos','idx','in_vor','vor_status']].round(1).to_string(index=False))
y=nv[nv.priced & ~nv.index.isin(NF[NF.idx.notna()].pid)]; print('VOR-priced NFL not priced in feed:',len(y)); print(y.sort_values('vor_value',ascending=False).head(10)[['name','pos','vor_value']].round(1).to_string())
dv=[]
for a in A:
    if a['population']=='devy': dv.append(dict(pos=a['position'],idx=fv(a)))
DV=pd.DataFrame(dv)
for p in ['QB','RB','WR','TE']:
    q=P[P.pos==p].sort_values('idx'); d=DV[(DV.pos==p)&DV.idx.notna()]
    print(p,'NFL pair idx range %.1f-%.1f'%(q.idx.min(),q.idx.max()),'| devy idx range %.1f-%.1f'%(d.idx.min(),d.idx.max()),
          '| devy below NFL min: %d of %d'%((d.idx<q.idx.min()).sum(),len(d)), '| lowest 5 NFL pairs (idx,vor):', list(zip(q.idx.round(1).head(5),q.vor.round(1).head(5))))
    # spearman of feed idx vs vor
# independent LOO with a different monotone estimator: step-function PAV (no centre interpolation)
def pav(x,y):
    o=np.argsort(x,kind='mergesort'); xs=np.asarray(x)[o]; ys=np.asarray(y,float)[o]
    v=[];w=[];n=[]
    for yi in ys:
        v.append(yi);w.append(1.);n.append(1)
        while len(v)>1 and v[-2]>v[-1]:
            a,b=v.pop(),v.pop();wa,wb=w.pop(),w.pop();na,nb=n.pop(),n.pop()
            v.append((a*wa+b*wb)/(wa+wb));w.append(wa+wb);n.append(na+nb)
    fit=np.repeat(v,n); return xs,fit
def step_pred(xs,fit,q):
    i=np.searchsorted(xs,q,side='right')-1
    if i<0: return fit[0]
    if i>=len(xs)-1: return fit[-1]
    # linear between adjacent fitted points
    x0,x1=xs[i],xs[i+1]; f0,f1=fit[i],fit[i+1]
    return f0 if x1==x0 else f0+(f1-f0)*(q-x0)/(x1-x0)
def rk(a): return pd.Series(np.asarray(a)).rank().values
def sp(a,b): return float(np.corrcoef(rk(a),rk(b))[0,1])
L=[]
for p in ['QB','RB','WR','TE']:
    q=P[P.pos==p].reset_index(drop=True)
    for i in range(len(q)):
        r=q.drop(i); xs,fit=pav(r.idx.values,r.vor.values); L.append(dict(pos=p,rk=q.rookie[i],v=q.vor[i],p=step_pred(xs,fit,q.idx[i]),raw=q.idx[i]))
L=pd.DataFrame(L)
print('my LOO spearman all %.4f, MAE %.1f; rookies n=%d spearman %.4f bias %.1f'%(sp(L.p,L.v),(L.p-L.v).abs().mean(),L.rk.sum(),sp(L[L.rk].p,L[L.rk].v),(L[L.rk].p-L[L.rk].v).mean()))
print('raw feed-index vs VOR spearman (no fit) all %.4f; within-pos:'%sp(L.raw,L.v), {p: round(sp(L[L.pos==p].raw,L[L.pos==p].v),4) for p in ['QB','RB','WR','TE']}, 'rookies %.4f'%sp(L[L.rk].raw,L[L.rk].v))
# how much of 0.96 is position-level separation? average within-position rho
print('within-pos LOO rho:', {p: round(sp(L[L.pos==p].p,L[L.pos==p].v),4) for p in ['QB','RB','WR','TE']})
# rookies-by-pos
R=L[L.rk]; print('rookies by pos:', {p:(int((R.pos==p).sum()), round(sp(R[R.pos==p].p,R[R.pos==p].v),3) if (R.pos==p).sum()>3 else None) for p in ['QB','RB','WR','TE']})
# rookies with low VOR vs high idx
P.to_csv(S+f'/review_vor/pairs_{mode}.csv',index=False)
