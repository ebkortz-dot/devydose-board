# independent rebuild of player-week fantasy points, all seasons
import pandas as pd, numpy as np, sys
D=sys.argv[1]
cols=['player_id','player_display_name','position','season','week','season_type','team','passing_yards','passing_tds','passing_interceptions','rushing_yards','rushing_tds','receptions','receiving_yards','receiving_tds','passing_2pt_conversions','rushing_2pt_conversions','receiving_2pt_conversions','sack_fumbles_lost','rushing_fumbles_lost','receiving_fumbles_lost','attempts','carries','targets']
fr=[]
for y in range(2012,2027):
    d=pd.read_csv(f'{D}/stats_{y}.csv',usecols=cols,low_memory=False)
    d=d[(d.season_type=='REG')&d.position.isin(['QB','RB','WR','TE'])]
    n=d.duplicated(['player_id','week']).sum()
    if n: print('DUP',y,n)
    f=lambda c:d[c].fillna(0)
    d['pts']=(f('passing_yards')*.04+f('passing_tds')*6-2*f('passing_interceptions')+f('rushing_yards')*.1+6*f('rushing_tds')+f('receptions')+.1*f('receiving_yards')+6*f('receiving_tds')+2*(f('passing_2pt_conversions')+f('rushing_2pt_conversions')+f('receiving_2pt_conversions'))-2*(f('sack_fumbles_lost')+f('rushing_fumbles_lost')+f('receiving_fumbles_lost')))
    fr.append(d[['player_id','player_display_name','position','season','week','team','pts']])
w=pd.concat(fr); w.to_parquet(f'{D}/../review/weeks.parquet') if False else w.to_pickle(sys.argv[2])
print(w.groupby('season').week.max().to_dict())
