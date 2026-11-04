import pandas as pd, numpy as np, sys
w=pd.read_pickle(sys.argv[1]); N=8
pl=pd.read_csv(sys.argv[2],usecols=['gsis_id','birth_date','draft_pick'],low_memory=False).drop_duplicates('gsis_id').set_index('gsis_id')
def agg(x): return x.groupby(['player_id','season']).pts.agg(['mean','size'])
early=agg(w[w.week<=N]).rename(columns={'mean':'early','size':'ge'})
ros=agg(w[w.week>N]).rename(columns={'mean':'t1','size':'g1'})
full=agg(w).rename(columns={'mean':'ppg','size':'g'})
pos=w.groupby(['player_id','season']).position.last()
R=early.join(ros).join(pos).reset_index()
R=R[(R.season>=2013)&(R.season<=2025)]
fp=full.reset_index()
prev=fp.assign(season=fp.season+1).set_index(['player_id','season'])
prev2=fp.assign(season=fp.season+2).set_index(['player_id','season'])
nxt=fp.assign(season=fp.season-1).set_index(['player_id','season'])
R=R.set_index(['player_id','season'])
R['prior']=prev.ppg.where(prev.g>=4); R['gp']=prev.g
R['p2']=prev2.ppg.where(prev2.g>=4); R['gp2']=prev2.g
R['t2']=nxt.ppg.where(nxt.g>=4); R['g2']=nxt.g
R['t1']=R.t1.where(R.g1>=3)
R=R.reset_index()
bd=pd.to_datetime(pl.birth_date,errors='coerce')
R['age']=(pd.to_datetime(R.season.astype(str)+'-09-01')-R.player_id.map(bd)).dt.days/365.25
R.to_pickle(sys.argv[3])
print(len(R), R.prior.notna().sum(), R.t1.notna().sum(), R.t2.notna().sum(), 'age missing', R.age.isna().sum())
