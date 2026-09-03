# -*- coding: utf-8 -*-
"""在「以门牌临街面为向」这一**假设**下，把坐向定到一个，并出盘。
   这是一个替代口径，不是玄空原本的定义——见 README 的三层说明。"""
import sys, json; sys.path.insert(0,'/home/user/Claude/fengshui/audit/geo')
import pipeline as P
C=json.load(open('city.json')); F=json.load(open('frontage.json'))
print(f"{'建筑':<16}{'运':>3}{'临街方位':>9}{'定向':>8}{'真山':>5}{'磁山':>5}{'坐山':>5}  格局      与次近候选的差")
for n,f in F.items():
    g=C[n]; xiang=f['best_cand']; d0=g['decl_build']
    mt=P.mountain_of(xiang)[0]; mm=P.mountain_of((xiang-d0)%360)[0]
    zuo=P.mountain_of((xiang+180)%360)[0]
    ge=P.chart(g['yun'], zuo, 'std')['ge']
    az=f['street_az']
    others=sorted(min(abs(c-az),360-abs(c-az)) for c in g['cands'])
    print(f"{n:<16}{g['yun']:>3}{az:>8.1f}°{xiang:>7.1f}°{mt:>5}{mm:>5}{zuo:>5}  {ge:<9} {others[0]:.1f}° vs {others[1]:.1f}°")
print("\n金茂大厦：OSM 无 addr:street —— 仍不判")
