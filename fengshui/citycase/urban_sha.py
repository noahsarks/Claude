# -*- coding: utf-8 -*-
"""第二层 · 城市砂：以建筑替代山水。
   依据 masters/cases/A04（杜金良：周围建筑就是「山」，须最高）
   与 C01（中银/汇丰：判据全是建筑几何，不含地形）。
   判断是零和相对的，所以只报相对量，不报绝对分。"""
import json, math
C = json.load(open('city.json')); NB = json.load(open('neighbors.json'))
HGT = {'上海中心大厦':632.0,'上海环球金融中心':492.0,'金茂大厦':420.5,'东方明珠电视塔':468.0,'台北101':508.0}
BA = ['北','东北','东','东南','南','西南','西','西北']
def oct_i(az): return int(((az + 22.5) % 360) // 45)

for site, key in (('陆家嘴','陆家嘴'), ('台北101','台北101')):
    rows = NB[key]
    print("="*76)
    print(f"{site}")
    print("="*76)
    for n, g in C.items():
        if site == '陆家嘴' and '台北' in n: continue
        if site == '台北101' and '台北' not in n: continue
        h0 = HGT[n]; la0, lo0 = g['lat'], g['lon']
        mx = 111320*math.cos(math.radians(la0)); my = 110540
        # 把邻楼坐标从站点中心系换算到本楼中心系
        base = (31.2366,121.5013) if site=='陆家嘴' else (25.0340,121.5645)
        cells = {i: [] for i in range(8)}
        for r in rows:
            # 还原邻楼绝对坐标
            ax = base[1] + (r['dist']*math.sin(math.radians(r['az'])))/mx
            ay = base[0] + (r['dist']*math.cos(math.radians(r['az'])))/my
            dx = (ax-lo0)*mx; dy = (ay-la0)*my
            d = math.hypot(dx, dy)
            if d < 25 or d > 1200: continue
            az = math.degrees(math.atan2(dx, dy)) % 360
            elev = math.degrees(math.atan2(r['h']-h0, d))   # 从本楼顶看邻楼顶的仰角
            cells[oct_i(az)].append((r['h'], d, az, elev, r['name']))
        print(f"\n── {n}　高 {h0} m　（半径 25–1200 m，仅计 OSM 有高度标注者）")
        print(f"   {'方':<5}{'邻楼数':>6}{'最高':>8}{'距':>7}{'仰角':>8}   最高者")
        tallest_any = None
        for i in range(8):
            v = cells[i]
            if not v:
                print(f"   {BA[i]:<5}{0:>6}{'—':>8}{'—':>7}{'—':>8}   （无有高度标注的邻楼——**不判**，缺数据）")
                continue
            v.sort(key=lambda x: -x[0]); h, d, az, el, nm = v[0]
            if tallest_any is None or h > tallest_any[0]: tallest_any = (h, nm)
            mark = '  ← 高于本楼' if h > h0 else ''
            print(f"   {BA[i]:<5}{len(v):>6}{h:>8.1f}{d:>7.0f}{el:>+8.1f}°   {nm[:18]}{mark}")
        if tallest_any and tallest_any[0] > h0:
            print(f"   ▸ 本楼**不是**周边最高：{tallest_any[1]} {tallest_any[0]} m 高于本楼 {tallest_any[0]-h0:.1f} m")
        else:
            print(f"   ▸ 本楼为半径 1200 m 内最高")
