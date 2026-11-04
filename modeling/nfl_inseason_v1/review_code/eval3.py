import pandas as pd, numpy as np, sys
R=pd.read_pickle(sys.argv[1]); R.loc[R.season==2025,'t2']=np.nan
V=R[R.prior.notna()]
K=[1,2,3,4,6,8,10,12,16,20,30,50]
SPL={'A':(range(2013,2019),range(2019,2026)),'B':(range(2019,2026),range(2013,2019))}
bl=lambda d,k:(k*d.prior+d['ge']*d.early)/(k+d['ge'])
for s,(tr,te) in SPL.items():
    trn=V[V.season.isin(tr)]; tst=V[V.season.isin(te)]
    for t in ('t1','t2'):
        a=trn[trn[t].notna()]; b=tst[tst[t].notna()]
        curve={k:round((bl(a,k)-a[t]).abs().mean(),3) for k in K}
        kt=min(curve,key=curve.get)
        print(s,t,'train-opt k',kt,'test MAE k=3',round((bl(b,3)-b[t]).abs().mean(),3),f'k={kt}',round((bl(b,kt)-b[t]).abs().mean(),3),'prior',round((b.prior-b[t]).abs().mean(),3))
# selection: retention for t1 by early-vs-prior quintile, vets
V=V.copy(); V['r']=V.early-V.prior; V['q']=pd.qcut(V.r,5,labels=False)
print(V.groupby('q').agg(r=('r','mean'),kept_t1=('t1',lambda s:s.notna().mean()),kept_t2=('t2',lambda s:s.notna().mean()),n=('r','size')).round(3))
