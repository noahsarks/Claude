# -*- coding: utf-8 -*-
"""取哈尔滨市辖区（admin_level=6）边界，用来把分析限定在「市区」而不是一个矩形框。

用户要的是松北、平房与主城区，不是整个哈尔滨地级市——阿城、玉泉在地级市内，
但不在「市区」里。用行政边界裁，比我画个框准。
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'citycase'))
import op
OUT = os.path.join(HERE, 'districts.json')
WANT = ['松北区', '道里区', '南岗区', '道外区', '香坊区', '平房区']

if __name__ == '__main__':
    if os.path.exists(OUT):
        print('已有', OUT); sys.exit(0)
    names = '|'.join(WANT)
    q = ('[out:json][timeout:300];'
         f'relation["admin_level"="6"]["name"~"^({names})$"](45.3,125.9,46.3,127.2);'
         'out geom;')
    d = op.q(q)
    if d is None: sys.exit('Overpass 取不到——中止，不猜边界')
    out = []
    for el in d.get('elements', []):
        nm = (el.get('tags') or {}).get('name', '')
        rings = []
        for m in el.get('members', []):
            g = m.get('geometry') or []
            if len(g) >= 2 and m.get('type') == 'way':
                rings.append([[p['lat'], p['lon']] for p in g])
        if rings:
            out.append(dict(name=nm, rings=rings))
    json.dump(out, open(OUT, 'w', encoding='utf8'), ensure_ascii=False)
    print(f'{len(out)} 个区 → {OUT}')
    for o in out:
        n = sum(len(r) for r in o['rings'])
        la = [p[0] for r in o['rings'] for p in r]; lo = [p[1] for r in o['rings'] for p in r]
        print(f"  {o['name']:<6} {len(o['rings']):3d} 段 {n:5d} 点  "
              f"纬 {min(la):.3f}–{max(la):.3f}  经 {min(lo):.3f}–{max(lo):.3f}")
