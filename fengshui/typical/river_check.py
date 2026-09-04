# -*- coding: utf-8 -*-
"""外部校核：DEM 汇流网络到底有没有把真实河流找出来。

必要性：v0.8 修了平地导流（填洼造出的严格平地上 D8 给不出方向，汇流在此中断）。
修完各点分数变化很大——但「变了」不等于「对了」。这里用 OSM 的 waterway=river
作为独立参照：取真实河道上的采样点，量它到「模型判出的水道」的距离。
修前修后各跑一次，距离中位数下降才算改进。
"""
import sys, os, math, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'citycase'))
import importlib, op

def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m

# 两个对照区：一个平原（洛阳盆地，缺陷应最重），一个山地（燕山南麓，作对照）
AREAS = {
    'luoyang_plain': dict(box=(34.55, 112.35, 34.85, 112.80), tile=(34, 112), zh='洛阳盆地(平原)'),
    'yanshan_mount': dict(box=(40.10, 116.05, 40.45, 116.55), tile=(40, 116), zh='燕山南麓(山地)'),
}

def rivers(name, box):
    CACHE = os.path.join(HERE, f'osm_rivers_{name}.json')
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding='utf8'))
    s, w, n, e = box
    q = f'[out:json][timeout:120];way["waterway"="river"]({s},{w},{n},{e});out geom;'
    d = op.q(q)
    if d is None: raise SystemExit('Overpass 取不到，检验中止（不猜）')
    pts = []
    for el in d.get('elements', []):
        g = el.get('geometry') or []
        for i, p in enumerate(g):
            if i % 5 == 0:                     # 每 5 个节点取一个，避免过密
                pts.append([p['lat'], p['lon']])
    json.dump(pts, open(CACHE, 'w'), ensure_ascii=False)
    return pts

def dist_to_network(engine_path, pts, tile):
    import kvamme as K
    for m in list(sys.modules):
        if m in ('lt_test', 'luantou'): del sys.modules[m]
    L = load(engine_path, 'luantou')          # kvamme 依赖 luantou.Region
    sys.modules['luantou'] = L
    importlib.reload(K)
    reg = K.Mosaic('t', range(tile[0], tile[0]+1), range(tile[1], tile[1]+1))
    out = []
    for la, lo in pts:
        if not (tile[0]+.05 < la < tile[0]+.95 and tile[1]+.05 < lo < tile[1]+.95): continue
        cr, cc = reg.crc(la, lo)
        d = np.hypot((reg.stream_rc[:, 0] - cr) * reg.cdy,
                     (reg.stream_rc[:, 1] - cc) * reg.cdx)
        out.append(float(d.min()))
    return np.array(out), reg

if __name__ == '__main__':
    for name, a in AREAS.items():
        pts = rivers(name, a['box'])
        print(f"\n【{a['zh']}】OSM waterway=river 采样点 {len(pts)} 个")
        for tag, path in (('修前 v0.7', os.path.join(os.path.dirname(HERE), 'luantou_v6.py')),
                          ('修后 v0.8', os.path.join(os.path.dirname(HERE), 'luantou.py'))):
            d, reg = dist_to_network(path, pts, a['tile'])
            if d.size == 0:
                print(f'  {tag}: 无点落在瓦片内'); continue
            print(f'  {tag}: n={d.size:4d}  中位 {np.median(d):6.0f} m  '
                  f'均值 {d.mean():6.0f} m  <240m 占 {np.mean(d<240)*100:5.1f}%  '
                  f'水道格 {len(reg.stream_rc):7,}  acc_max {np.nanmax(reg.acc_km2):5.0f} km²')
