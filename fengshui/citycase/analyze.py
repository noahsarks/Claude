# -*- coding: utf-8 -*-
"""上海陆家嘴与台北101：按本项目现有结论逐层分析。

三层诚实防线（抄自 Horosa neijuDetect，见 audit/existing_software.md）：
  ① 只对有充分输入的项给判定，缺输入就列出缺什么，绝不用「没检测到」冒充「没有」
  ② 每条给证据（度数、距离、仰角、比值），可逐条复核
  ③ 判定是建议，不覆盖人工勘测
"""
import sys, json, math
sys.path.insert(0, '/home/user/fs')
sys.path.insert(0, '/home/user/Claude/fengshui/audit/geo')
import pipeline as P
import numpy as np

C = json.load(open('/home/user/city/city.json'))
NB = json.load(open('/home/user/city/neighbors.json'))
YS = P.SHAN

def mountain(deg):
    return P.mountain_of(deg % 360)[0]

def frame(true_az, decl_east):
    """真方位 → 罗盘（磁）方位。真 = 磁 + 偏(东正) ⇒ 磁 = 真 − 偏"""
    return (true_az - decl_east) % 360

BA = ['北','东北','东','东南','南','西南','西','西北']
def octant(az): return BA[int(((az + 22.5) % 360) // 45)]

print("="*76)
print("第一层 · 理气（本项目已四端点互证的部分）")
print("="*76)
print("""
可算的前提：元运由建成年定（本盘定终身不变），24 山由坐向度数定。
缺的输入：**坐向**。OSM 轮廓只能约束到四个候选朝向（法线方向），
          要定到一个需要入户门位置或实地罗盘读数——**本次没有，故不臆断**。
          （依 masters/analysis.md 结论三：坐向是输入，不从地形反推。）
""")
for n, g in C.items():
    print(f"── {n}　建成 {g['year']}　{g['yun']} 运　({g['lat']}, {g['lon']})")
    print(f"   轮廓主轴 {g['axis']:.1f}°（真北系，OSM 实测 {g['n_edges']} 条边，周长 {g['perim']} m）")
    if n == '东方明珠电视塔':
        print("   ⚠ 圆形塔身（169 条边），主轴无意义 —— 此项不判，缺「可辨识的立面朝向」")
        print()
        continue
    d_b, d_n = g['decl_build'], g['decl_2026']
    print(f"   磁偏角：建成年 {d_b:+.2f}°（IGRF）　2026 年 {d_n:+.2f}°　"
          f"十余年漂移 {abs(d_n-d_b):.2f}° = {abs(d_n-d_b)/15*100:.0f}% 个山")
    print(f"   {'候选向':>8}{'真北山':>7}{'磁北山':>7}  {'坐山':>4}  {g['yun']}运格局")
    for c in g['cands']:
        mt_true = mountain(c)
        mt_mag = mountain(frame(c, d_b))
        zuo_true = mountain(c + 180)
        try:
            ge = P.chart(g['yun'], zuo_true, 'std')['ge']
        except Exception:
            ge = '?'
        flag = '' if mt_true == mt_mag else '  ← 真/磁不同山'
        print(f"   {c:7.1f}°{mt_true:>7}{mt_mag:>7}  {zuo_true:>4}  {ge}{flag}")
    print()

print("="*76)
print("第一层补充 · 真/磁两系分歧对格局的影响（只有上海中心受影响）")
print("="*76)
g = C['上海中心大厦']
print(f"上海中心大厦　8 运　主轴 50.5°　建成年磁偏角 {g['decl_build']:+.2f}°\n")
print(f"   {'候选向':>8}{'真北':>5}{'格局(真)':>10}{'磁北':>5}{'格局(磁)':>10}   一致?")
for c in g['cands']:
    zt = mountain(c + 180); zm = mountain(frame(c, g['decl_build']) + 180)
    gt = P.chart(8, zt, 'std')['ge']; gm = P.chart(8, zm, 'std')['ge']
    print(f"   {c:7.1f}°{zt:>5}{gt:>10}{zm:>5}{gm:>10}   {'✓' if gt==gm else '✗ 不一致'}")
print("""
   注：艮/寅、巽/巳、坤/申、乾/亥 分属天元龙与人元龙，挨星顺逆由元龙定，
   故越界不只是换个山名，是整盘重排。
   —— 这正是 audit/geo/README.md 量化过的那个问题，在一栋真实建筑上的体现。
""")
