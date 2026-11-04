import pandas as pd, numpy as np, sys
R=pd.read_pickle(sys.argv[1]); R.loc[R.season==2025,'t2']=np.nan
V=R[R.prior.notna()].copy()  # veterans only
P=['QB','RB','WR','TE']; K=[1,2,3,4,6,8,10,12,16,20,30,50,80]
SPL={'A':(range(2013,2019),range(2019,2026)),'B':(range(2019,2026),range(2013,2019))}
def rho(a,b): return pd.Series(np.asarray(a)).rank().corr(pd.Series(np.asarray(b)).rank())
def bl(df,pr,k): return (k*pr+df['ge']*df.early)/(k+df['ge'])
def feats(df):
    p2=df.p2.fillna(df.prior); a=df.age.clip(20,40)
    return np.column_stack([np.ones(len(df)),df.prior,p2,a,a**2,(df.gp>=12).astype(float)])
res={}
for s,(tr,te) in SPL.items():
    trn=V[V.season.isin(tr)].copy(); tst=V[V.season.isin(te)].copy()
    for t in ('t1','t2'):
        tr_t=trn[trn[t].notna()]; te_t=tst[tst[t].notna()].copy()
        # strong baseline per position, fitted on train target t
        sb=pd.Series(index=te_t.index,dtype=float); sbtr=pd.Series(index=tr_t.index,dtype=float)
        for p in P:
            m=tr_t.position==p; X=feats(tr_t[m]); b=np.linalg.lstsq(X,tr_t.loc[m,t],rcond=None)[0]
            sbtr[m]=X@b; mt=te_t.position==p; sb[mt]=feats(te_t[mt])@b
        k0=min(K,key=lambda k:(bl(tr_t,tr_t.prior,k)-tr_t[t]).abs().mean())
        kS=min(K,key=lambda k:(bl(tr_t,sbtr,k)-tr_t[t]).abs().mean())
        te_t['raw']=te_t.prior; te_t['sb']=sb; te_t['bl_raw3']=bl(te_t,te_t.prior,3); te_t['bl_sb']=bl(te_t,sb,kS)
        for g in ['all']+P:
            x=te_t if g=='all' else te_t[te_t.position==g]
            m=lambda c:(x[c]-x[t]).abs().mean()
            res.setdefault((t,g),[]).append(dict(n=len(x),kS=kS,
               raw_vs_sb_mae=round(m('sb')-m('raw'),3),
               blend3_vs_sb_mae=round(m('bl_raw3')-m('sb'),3), blend3_vs_sb_rho=round(rho(x.bl_raw3,x[t])-rho(x.sb,x[t]),4),
               blendSB_vs_sb_mae=round(m('bl_sb')-m('sb'),3), blendSB_vs_sb_rho=round(rho(x.bl_sb,x[t])-rho(x.sb,x[t]),4)))
for c,v in res.items():
    print(c,'n',[d['n'] for d in v],'kS',[d['kS'] for d in v],
      '| SB-raw MAE',[d['raw_vs_sb_mae'] for d in v],
      '| author blend vs SB: worst dMAE',max(d['blend3_vs_sb_mae'] for d in v),'worst dRho',min(d['blend3_vs_sb_rho'] for d in v),
      '| blend(SB) vs SB: worst dMAE',max(d['blendSB_vs_sb_mae'] for d in v),'worst dRho',min(d['blendSB_vs_sb_rho'] for d in v))
