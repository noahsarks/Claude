# -*- coding: utf-8 -*-
"""差异归因：把三个引擎的结论分歧，拆成「地理步骤」与「挨星步骤」两个来源。
   做法：扫过全部罗盘读数（0-360, 0.1°），分别统计
     A 只因磁偏角不同 → 坐山不同
     B 坐山相同、只因挨星规则不同 → 格局不同
     C 两者都有"""
import numpy as np, json
import pipeline as P

STEP = 0.1
mags = np.arange(0, 360, STEP)
print(f"九运，扫 {len(mags)} 个罗盘读数（0.1° 步长）\n")
print(f"{'城市':<9}{'坐山分歧':>10}{'其中 fs-hr':>11}{'fs-sg':>8}{'格局分歧':>10}{'仅挨星致':>10}")
rows = []
for city in ['洛阳', '杭州', '北京', '哈尔滨', '广州', '乌鲁木齐', '拉萨', '西安']:
    dz = dz_fh = dz_fs = dg = dg_only_rule = 0
    for m in mags:
        r = P.run(city, float(m))
        z = {e: r[e]['zuo'] for e in r}
        g = {e: r[e]['ge'] for e in r}
        if len(set(z.values())) > 1: dz += 1
        if z['fscalc'] != z['horosa']: dz_fh += 1
        if z['fscalc'] != z['suangua']: dz_fs += 1
        if len(set(g.values())) > 1:
            dg += 1
            if len(set(z.values())) == 1: dg_only_rule += 1
    n = len(mags)
    rows.append((city, dz/n, dz_fh/n, dz_fs/n, dg/n, dg_only_rule/n))
    print(f"{city:<9}{dz/n*100:>9.1f}%{dz_fh/n*100:>10.1f}%{dz_fs/n*100:>7.1f}%"
          f"{dg/n*100:>9.1f}%{dg_only_rule/n*100:>9.1f}%")

print("\n对照：理论值 = |磁偏角之差| / 15°（山宽）")
D = {r['name']: r for r in json.load(open('decl.json'))}
for city, *_ in rows:
    d = D[city]
    fh = abs(-d['noaa_east'] - d['horosa2013']) / 15
    fs = abs(d['noaa_east']) / 15
    print(f"  {city:<9} fscalc-Horosa {fh*100:5.1f}%   fscalc-suangua(不校正) {fs*100:5.1f}%")
