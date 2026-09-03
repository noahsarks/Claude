# -*- coding: utf-8 -*-
"""用「门牌所在街道」定正面：取 addr:street 命名的道路，算它相对建筑质心在哪个方位。
   这是建筑学意义上的 frontage（临街面），不是玄空的「向」——两者可能一致，也可能不。"""
import sys, json, math; sys.path.insert(0,'/home/user/city')
from op import q
G=json.load(open('city.json'))
ADDR={'上海中心大厦':('银城中路',31.2356,121.5013),
      '上海环球金融中心':('世纪大道',31.2366,121.5030),
      '金茂大厦':(None,31.2373,121.5014),
      '台北101':('信義路五段',25.0340,121.5646)}
def bearing(la0,lo0,la,lo):
    mx=111320*math.cos(math.radians(la0)); my=110540
    return math.degrees(math.atan2((lo-lo0)*mx,(la-la0)*my))%360
BA=['北','东北','东','东南','南','西南','西','西北']
out={}
for n,(street,la0,lo0) in ADDR.items():
    if not street:
        print(f"── {n}：OSM 无 addr:street —— **不判**，缺门牌街道"); continue
    Q=f'[out:json][timeout:60];way["highway"]["name"="{street}"](around:600,{la0},{lo0});out geom;'
    d=q(Q)
    if not d or not d.get('elements'):
        print(f"── {n}：未取到「{street}」几何 —— 不判"); continue
    pts=[]
    for e in d['elements']:
        for p in e.get('geometry',[]) or []:
            mx=111320*math.cos(math.radians(la0)); my=110540
            dd=math.hypot((p['lon']-lo0)*mx,(p['lat']-la0)*my)
            if dd<=600: pts.append((dd,bearing(la0,lo0,p['lat'],p['lon'])))
    if not pts:
        print(f"── {n}：「{street}」在 600 m 内无点 —— 不判"); continue
    pts.sort()
    near=pts[:max(3,len(pts)//10)]
    # 圆均值
    s=sum(math.sin(math.radians(b)) for _,b in near); c=sum(math.cos(math.radians(b)) for _,b in near)
    az=math.degrees(math.atan2(s,c))%360
    d0=near[0][0]
    cands=G[n]['cands'] if n in G else []
    best=min(cands, key=lambda x: min(abs(x-az),360-abs(x-az))) if cands else None
    err=min(abs(best-az),360-abs(best-az)) if best is not None else None
    out[n]=dict(street=street, street_az=round(az,1), dist=round(d0), best_cand=best, err=err)
    print(f"── {n}")
    print(f"   门牌街道「{street}」最近点 {d0:.0f} m，方位 {az:.1f}°（{BA[int(((az+22.5)%360)//45)]}）")
    print(f"   轮廓四候选 {['%.1f°'%c for c in cands]}")
    print(f"   → 最接近的候选：{best:.1f}°，差 {err:.1f}°")
json.dump(out, open('frontage.json','w'), ensure_ascii=False, indent=1)
