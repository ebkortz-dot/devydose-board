import pandas as pd, numpy as np, sys
R=pd.read_pickle(sys.argv[1]); R.loc[R.season==2025,'t2']=np.nan
pl=pd.read_csv(sys.argv[2],usecols=['gsis_id','draft_pick','rookie_season','draft_year'],low_memory=False).drop_duplicates('gsis_id').set_index('gsis_id')
N=R[R.prior.isna()].copy()
N['lp']=np.log(N.player_id.map(pl.draft_pick).fillna(260.0))
N['rook']=N.player_id.map(pl.rookie_season)==N.season
P=['QB','RB','WR','TE']; K=[1,2,3,4,6,8,10,12,16,20,30,50]
rho=lambda a,b: a.rank().corr(b.rank())
for s,(tr,te) in {'A':(range(2013,2019),range(2019,2026)),'B':(range(2019,2026),range(2013,2019))}.items():
    a=N[N.season.isin(tr)].copy(); b=N[N.season.isin(te)].copy()
    # fit prior on train: target = t1 if present else early (author's choice) and also on t1-only (cleaner)
    for name,ycol in (('author',None),('t1only','t1')):
        co={}
        for p in P:
            x=a[a.position==p]; y=x.t1.fillna(x.early) if ycol is None else x.t1
            m=y.notna(); co[p]=np.polyfit(x.lp[m],y[m],1)
        pr=lambda d:np.maximum(d.position.map(lambda p:co[p][1])+d.position.map(lambda p:co[p][0])*d.lp,0.5)
        a['pr']=pr(a); b['pr']=pr(b)
        bl=lambda d,k:(k*d.pr+d['ge']*d.early)/(k+d['ge'])
        k=min(K,key=lambda k:sum((bl(a,k)-a[t]).abs().mean() for t in ('t1','t2')))
        out=[]
        for t in ('t1','t2'):
            for g in ['all']+P+['rookies','nonrookies']:
                x=b[b[t].notna()]
                if g in P: x=x[x.position==g]
                if g=='rookies': x=x[x.rook]
                if g=='nonrookies': x=x[~x.rook]
                bb=bl(x,k)
                out.append(f"{t}/{g} n={len(x)} dMAE={(bb-x[t]).abs().mean()-(x.pr-x[t]).abs().mean():.3f} dRho={rho(bb,x[t])-rho(x.pr,x[t]):.3f}")
        print(s,name,'k',k,'\n  '+'\n  '.join(out))
