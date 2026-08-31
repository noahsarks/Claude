import json, urllib.parse, urllib.request, time
EP="https://query.wikidata.org/sparql"
def q(sparql):
    u=EP+"?"+urllib.parse.urlencode({"query":sparql,"format":"json"})
    r=urllib.request.Request(u,headers={"Accept":"application/sparql-results+json","User-Agent":"fengshui-research/0.1"})
    return json.load(urllib.request.urlopen(r,timeout=180))
rows=[]
for off in range(0,7000,1500):
    s=f'''SELECT ?s ?sLabel ?c ?admLabel WHERE {{
      ?s wdt:P1435 wd:Q1188574 ; wdt:P625 ?c .
      OPTIONAL {{ ?s wdt:P131 ?adm . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,zh-hans,en". }}
    }} LIMIT 1500 OFFSET {off}'''
    d=q(s); b=d['results']['bindings']
    print("offset",off,"->",len(b),flush=True)
    for x in b:
        pt=x['c']['value']            # Point(lon lat)
        lon,lat=pt.replace('Point(','').replace(')','').split()
        rows.append({"qid":x['s']['value'].split('/')[-1],
                     "name":x.get('sLabel',{}).get('value',''),
                     "adm":x.get('admLabel',{}).get('value',''),
                     "lat":float(lat),"lon":float(lon)})
    if len(b)<1500: break
    time.sleep(1)
# 去重
seen={}
for r in rows: seen[r['qid']]=r
rows=list(seen.values())
json.dump(rows,open('guobao.json','w'),ensure_ascii=False)
print("总计",len(rows))
import collections
kw=collections.Counter()
for r in rows:
    n=r['name']
    for k in ['陵','墓','寺','庙','塔','故城','遗址','桥','祠','窑','石窟','民居','村','书院','衙','城墙']:
        if k in n: kw[k]+=1
print(dict(kw.most_common()))
