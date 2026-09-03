# -*- coding: utf-8 -*-
"""给 guobao.json 补「年代」与「对象类型」——轴 1 与轴 2 的前置条件。
   来源：Wikidata P31(instance of) / P571(inception) / P2348(time period)。CC0。"""
import json, subprocess, time, urllib.parse, os
UA = "FengshuiResearchBot/0.1 (heritage-site metadata; research)"
EP = "https://query.wikidata.org/sparql"
sites = json.load(open('/home/user/fs/guobao.json', encoding='utf8'))
qids = [s['qid'] for s in sites]
print('待查', len(qids))

def batch(qs):
    vals = ' '.join(f'wd:{q}' for q in qs)
    Q = f"""SELECT ?item ?p31Label ?inception ?periodLabel WHERE {{
  VALUES ?item {{ {vals} }}
  OPTIONAL {{ ?item wdt:P31 ?p31 }}
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P2348 ?period }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,zh-hans,en". }}
}}"""
    for a in range(4):
        r = subprocess.run(["curl","-sS","-m","180","-A",UA,
                            "-H","Accept: application/sparql-results+json",
                            "--data-urlencode",f"query={Q}", EP], capture_output=True, text=True)
        if r.stdout.strip().startswith("{"):
            try: return json.loads(r.stdout)
            except Exception: pass
        time.sleep(5*(a+1))
    return None

out = {}
CH = 200
for i in range(0, len(qids), CH):
    d = batch(qids[i:i+CH])
    if not d:
        print(f'  批 {i//CH} 失败'); continue
    for b in d['results']['bindings']:
        q = b['item']['value'].rsplit('/',1)[-1]
        e = out.setdefault(q, {'p31': set(), 'inception': None, 'period': set()})
        if 'p31Label' in b: e['p31'].add(b['p31Label']['value'])
        if 'inception' in b and not e['inception']: e['inception'] = b['inception']['value'][:10]
        if 'periodLabel' in b: e['period'].add(b['periodLabel']['value'])
    if (i//CH) % 5 == 0: print(f'  {i+CH}/{len(qids)}  已得 {len(out)}', flush=True)
    time.sleep(1)
res = {q: {'p31': sorted(v['p31']), 'inception': v['inception'], 'period': sorted(v['period'])}
       for q, v in out.items()}
json.dump(res, open('/home/user/fs/wd_meta.json','w'), ensure_ascii=False)
have_t = sum(1 for v in res.values() if v['p31'])
have_y = sum(1 for v in res.values() if v['inception'] or v['period'])
print(f"\n完成：{len(res)} 条；有类型 {have_t}（{have_t/len(qids)*100:.0f}%）；有年代 {have_y}（{have_y/len(qids)*100:.0f}%）")
