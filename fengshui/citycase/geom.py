# -*- coding: utf-8 -*-
"""从 OSM 轮廓算：质心、边长加权的主轴方位、以及由此约束出的坐向候选。
   坐向不从地形反推（masters/analysis.md 结论三），只由建筑几何给出候选集。"""
import json, math, numpy as np
B = json.load(open('/home/user/city/osm_buildings.json'))
KEEP = {'上海中心大厦','上海环球金融中心','金茂大厦','东方明珠电视塔','台北101'}

def centroid(g):
    la = sum(p[0] for p in g)/len(g); lo = sum(p[1] for p in g)/len(g)
    return la, lo

def edges(g, la0):
    mx = 111320*math.cos(math.radians(la0)); my = 110540
    out=[]
    for i in range(len(g)-1):
        dx=(g[i+1][1]-g[i][1])*mx; dy=(g[i+1][0]-g[i][0])*my
        L=math.hypot(dx,dy)
        if L<1: continue
        az=(math.degrees(math.atan2(dx,dy)))%180   # 边的走向 0-180
        out.append((L,az))
    return out

print(f"{'建筑':<16}{'纬度':>9}{'经度':>10}{'边数':>5}{'总边长':>8}  主轴(mod90)  坐向候选（法线方向）")
res={}
for b in B:
    if b['name'] not in KEEP: continue
    g=b['geom']; la,lo=centroid(g)
    E=edges(g,la)
    if not E: continue
    # 边长加权的 mod-90 方向直方图（0.5° 分辨）
    H=np.zeros(180)
    for L,az in E:
        H[int((az%90)*2)] += L
    H=np.convolve(np.r_[H,H,H], np.ones(5)/5, 'same')[180:360]
    k=int(np.argmax(H)); axis=k/2.0
    tot=sum(L for L,_ in E)
    # 法线：轴向 ±90，四个候选朝向
    cands=sorted({(axis+d)%360 for d in (0,90,180,270)})
    res[b['name']]=dict(lat=round(la,5), lon=round(lo,5), axis=axis, cands=cands,
                        height=b.get('height'), n_edges=len(E), perim=round(tot))
    print(f"{b['name']:<16}{la:9.5f}{lo:10.5f}{len(E):>5}{tot:8.0f}m  {axis:6.1f}°     "
          + " / ".join(f"{c:.1f}°" for c in cands))
json.dump(res, open('/home/user/city/geom.json','w'), ensure_ascii=False, indent=1)
