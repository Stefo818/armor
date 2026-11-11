import json, numpy as np, pandas as pd
sp=pd.read_csv('data/series/sp500.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
t=pd.read_csv('data/titan_storia.csv',index_col=0,parse_dates=True)
sp=sp.reindex(t.index,method='ffill')
H=63
fmin=pd.Series([sp.iloc[i+1:i+H+1].min()/sp.iloc[i]-1 if i+H<len(sp) else np.nan for i in range(len(sp))],index=sp.index)
fret=sp.shift(-H)/sp-1
out={}
for col in ['armor_index','super_armor_index']:
    x=t[col]; d=pd.DataFrame({'x':x,'dd':fmin,'r':fret}).dropna()
    d=d[d.index>='1995-01-01']
    res={'quantili':{q:round(float(x.quantile(q)),1) for q in (.1,.25,.5,.75,.9,.95)},'fasce':[]}
    edges=[0,25,30,35,40,45,50,55,60,70,101]
    for a,b in zip(edges[:-1],edges[1:]):
        s=d[(d.x>=a)&(d.x<b)]
        if len(s)<60: continue
        res['fasce'].append({'da':a,'a':b,'n':len(s),'quota_giorni_%':round(100*len(s)/len(d),1),'calo10_%':round(100*(s.dd<=-.10).mean(),1),'calo5_%':round(100*(s.dd<=-.05).mean(),1),'peggior_medio_%':round(100*s.dd.mean(),1),'ritorno_med_%':round(100*s.r.median(),1)})
    out[col]=res
    print(col,res['quantili']);[print(f) for f in res['fasce']]
print('base calo10 %',round(100*(d.dd<=-.10).mean(),1))
json.dump(out,open('scratch/soglie_titan.json','w'),indent=1)

print('--- zone scelte')
Z={'armor_index':[0,35,40,45,101],'super_armor_index':[0,35,45,55,101]}
zs={}
for col,e in Z.items():
    x=t[col]; d=pd.DataFrame({'x':x,'dd':fmin}).dropna(); d=d[d.index>='1995-01-01']
    zs[col]=[]
    for a,b in zip(e[:-1],e[1:]):
        s=d[(d.x>=a)&(d.x<b)]
        zs[col].append({'da':a,'a':b,'giorni_%':round(100*len(s)/len(d)),'calo10_%':round(100*(s.dd<=-.10).mean()),'peggior_medio_%':round(100*s.dd.mean(),1)})
    print(col,zs[col])
json.dump(zs,open('scratch/zone_titan.json','w'),indent=1)
