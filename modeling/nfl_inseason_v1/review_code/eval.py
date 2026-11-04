import pandas as pd, numpy as np, sys
R=pd.read_pickle(sys.argv[1]); R.loc[R.season==2025,'t2']=np.nan
P=['QB','RB','WR','TE']; K=[1,2,3,4,6,8,10,12,16,20,30]
SPL={'A':(range(2013,2019),range(2019,2026)),'B':(range(2019,2026),range(2013,2019))}
def rho(a,b): return pd.Series(a).rank().corr(pd.Series(b).rank())  # tie-averaged Spearman
def rho_notie(a,b):  # replicate author's tie handling (stable sort order)
    a=pd.Series(a).rank(method='first'); b=pd.Series(b).rank(method='first'); return a.corr(b)
def blend(df,pr,k): return (k*pr+df['ge']*df.early)/(k+df['ge'])
out={}
for s,(tr,te) in SPL.items():
    trn=R[R.season.isin(tr)]; tst=R[R.season.isin(te)].copy()
    rm=trn[trn.prior.isna()].groupby('position').early.mean()
    def prf(df): return df.prior.fillna(df.position.map(rm))
    obj=lambda k: sum((blend(trn,prf(trn),k)-trn[t]).abs().mean() for t in ('t1','t2'))
    k=min(K,key=obj); tst['pr']=prf(tst); tst['bl']=blend(tst,tst.pr,k)
    print(s,'k',k,rm.round(2).to_dict())
    for t in ('t1','t2'):
        for g in ['all']+P+['vets','no_prior']:
            x=tst[tst[t].notna()]
            if g in P: x=x[x.position==g]
            if g=='vets': x=x[x.prior.notna()]
            if g=='no_prior': x=x[x.prior.isna()]
            dm=(x.bl-x[t]).abs().mean()-(x.pr-x[t]).abs().mean()
            out.setdefault((t,g),[]).append((len(x),round(dm,3),round(rho(x.bl,x[t])-rho(x.pr,x[t]),4),round(rho_notie(x.bl,x[t])-rho_notie(x.pr,x[t]),4)))
for c,v in out.items(): print(c,'n',[a[0] for a in v],'worst dMAE',max(a[1] for a in v),'worst dRho(tie-avg)',min(a[2] for a in v),'worst dRho(author ties)',min(a[3] for a in v))
