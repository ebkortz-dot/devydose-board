import pandas as pd, numpy as np, sys
w=pd.read_pickle(sys.argv[1]); R=pd.read_pickle(sys.argv[2]); R.loc[R.season==2025,'t2']=np.nan
tw=w[['season','week','team']].drop_duplicates()
team8=w[w.week<=8].sort_values('week').groupby(['player_id','season']).team.last()
ros_tg=tw[tw.week>8].groupby(['season','team']).size()
rospts=w[w.week>8].groupby(['player_id','season']).pts.sum()
nxtpts=w.groupby(['player_id','season']).pts.sum()
seasg=tw.groupby('season').apply(lambda d:d.groupby('team').size().max())
R=R.set_index(['player_id','season'])
R['tm']=team8
R['T1z']=[rospts.get(i,0.0)/ros_tg.get((i[1],R.at[i,'tm']),np.nan) for i in R.index]
R['T2z']=[nxtpts.get((i[0],i[1]+1),0.0)/seasg.get(i[1]+1,np.nan) for i in R.index]
R=R.reset_index(); R.loc[R.season==2025,'T2z']=np.nan
V=R[R.prior.notna()]
rho=lambda a,b: a.rank().corr(b.rank())
for s,te in {'A':range(2019,2026),'B':range(2013,2019)}.items():
    x=V[V.season.isin(te)]
    b=(3*x.prior+x['ge']*x.early)/(3+x['ge'])
    for t,tt in (('T1z','t1'),('T2z','t2')):
        m=x[t].notna(); m2=x[tt].notna()
        print(s,t,'n',m.sum(),'dRho incl dropouts(0)',round(rho(b[m],x.loc[m,t])-rho(x.prior[m],x.loc[m,t]),4),
              '| original sel n',m2.sum(),round(rho(b[m2],x.loc[m2,tt])-rho(x.prior[m2],x.loc[m2,tt]),4))
