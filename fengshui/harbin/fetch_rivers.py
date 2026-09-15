# -*- coding: utf-8 -*-
"""取哈尔滨一带 OSM waterway=river 几何。

为什么必须取：松花江在哈尔滨的流域上万 km²，但它的上游在瓦片范围之外，
DEM 汇流累积在瓦片边界处从零起算，所以无论修不修平地导流，
瓦片内都看不出松花江是「幹」。引擎因此判「不判(汇流网络未见干水)」——
这是正确的弃权，但《水龙经》平洋法的第一条就用不上了。
解法是拿外部数据给「幹」，而不是把阈值调低去迁就坏数据。
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'citycase'))
import op

BOX = (45.20, 125.80, 46.30, 127.50)      # s, w, n, e —— 比分析框各放宽约 0.2°
OUT = os.path.join(HERE, 'osm_rivers_harbin.json')

if __name__ == '__main__':
    if os.path.exists(OUT):
        print('已有', OUT); sys.exit(0)
    s, w, n, e = BOX
    # river/canal 给「幹」的候选，stream/ditch 给「支」——
    # 「以通流大水為行龍而為幹，溝渠小水為割界而為支」，支本来就是沟渠。
    q = (f'[out:json][timeout:300];'
         f'(way["waterway"="river"]({s},{w},{n},{e});'
         f' way["waterway"="canal"]({s},{w},{n},{e});'
         f' way["waterway"="stream"]({s},{w},{n},{e});'
         f' way["waterway"="ditch"]({s},{w},{n},{e}););out geom;')
    d = op.q(q)
    if d is None:
        sys.exit('Overpass 取不到——不猜，直接中止')
    ways = []
    for el in d.get('elements', []):
        g = el.get('geometry') or []
        if len(g) < 2: continue
        ways.append(dict(name=(el.get('tags') or {}).get('name', ''),
                         kind=(el.get('tags') or {}).get('waterway', ''),
                         pts=[[p['lat'], p['lon']] for p in g]))
    json.dump(ways, open(OUT, 'w', encoding='utf8'), ensure_ascii=False)
    npts = sum(len(w['pts']) for w in ways)
    print(f'{len(ways)} 条水道，{npts} 个节点 → {OUT}')
    from collections import Counter
    for nm, c in Counter(w['name'] for w in ways if w['name']).most_common(12):
        print(f'   {nm}  {c} 段')
