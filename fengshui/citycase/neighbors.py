# -*- coding: utf-8 -*-
"""城市砂：周边建筑的高度与方位。
   依据 masters/cases/A04——城市实践中建筑替换山水，判断是零和相对的
   （杜金良：周围建筑就是「山」，新厂房必须最高且朝南）。"""
import json, math, subprocess, time
UA="FengshuiResearch/0.1 (research)"
def overpass(q):
    for ep in ("https://overpass-api.de/api/interpreter",
               "https://overpass.kumi.systems/api/interpreter"):
        for a in range(3):
            o=subprocess.run(["curl","-sS","-m","150","-A",UA,"-X","POST","--data-urlencode",
                              f"data={q}",ep],capture_output=True,text=True).stdout
            if o.startswith("{"):
                return json.loads(o)
            time.sleep(3)
    return None

SITES={'陆家嘴': (31.2366,121.5013,1200), '台北101': (25.0340,121.5645,1200)}
res={}
for name,(la,lo,R) in SITES.items():
    q=f'[out:json][timeout:120];way(around:{R},{la},{lo})["building"]["height"];out center tags;'
    d=overpass(q)
    if not d: print(name,'查询失败'); continue
    mx=111320*math.cos(math.radians(la)); my=110540
    rows=[]
    for e in d.get('elements',[]):
        c=e.get('center') or {}
        t=e.get('tags',{})
        try: h=float(str(t.get('height','')).replace('m','').strip())
        except Exception: continue
        if not c: continue
        dx=(c['lon']-lo)*mx; dy=(c['lat']-la)*my
        rows.append(dict(name=t.get('name') or t.get('name:en') or '(无名)', h=h,
                         dist=round(math.hypot(dx,dy)), az=round(math.degrees(math.atan2(dx,dy))%360,1)))
    rows.sort(key=lambda r:-r['h'])
    res[name]=rows
    print(f"\n=== {name} 半径 {R}m 内有高度标注的建筑 {len(rows)} 座（按高度） ===")
    for r in rows[:14]:
        print(f"  {r['h']:>6.1f}m  {r['dist']:>5}m  方位 {r['az']:>5.1f}°  {r['name'][:26]}")
json.dump(res, open('neighbors.json','w'), ensure_ascii=False, indent=1)
