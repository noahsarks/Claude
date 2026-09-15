# -*- coding: utf-8 -*-
"""取分析框内的 OSM 地名，用来给「评分最高的区域」起名字。

只标坐标不给地名的图没法看——读图的人要知道那块高分区在哪儿。
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'citycase'))
import op
BOX = (45.30, 125.95, 46.20, 127.35)
OUT = os.path.join(HERE, 'osm_places_harbin.json')
if __name__ == '__main__':
    if os.path.exists(OUT):
        print('已有', OUT); sys.exit(0)
    s, w, n, e = BOX
    q = ('[out:json][timeout:180];('
         f'node["place"~"^(city|town|suburb|village|county)$"]({s},{w},{n},{e});'
         f'node["natural"="peak"]({s},{w},{n},{e});'
         ');out;')
    d = op.q(q)
    if d is None: sys.exit('Overpass 取不到——中止')
    out = []
    for el in d.get('elements', []):
        t = el.get('tags') or {}
        nm = t.get('name')
        if not nm: continue
        out.append(dict(lat=el['lat'], lon=el['lon'], name=nm,
                        kind=t.get('place') or t.get('natural'),
                        ele=t.get('ele')))
    json.dump(out, open(OUT, 'w', encoding='utf8'), ensure_ascii=False)
    from collections import Counter
    print(len(out), '个地名 →', OUT, dict(Counter(x['kind'] for x in out)))
