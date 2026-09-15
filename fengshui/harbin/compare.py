# -*- coding: utf-8 -*-
"""两套规则在哈尔滨格网上的一致性与分歧。"""
import os, sys, json, math
import numpy as np
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))

scope = sys.argv[1] if len(sys.argv) > 1 else 'city'
d = json.load(open(os.path.join(HERE, f'grid_{scope}.json'), encoding='utf8'))
rows = [r for r in d['rows'] if r]
M = np.array([r['modern'] for r in rows])
Z = np.array([r['zjy'] for r in rows])
lat = np.array([r['lat'] for r in rows]); lon = np.array([r['lon'] for r in rows])
mode = np.array([r['mode'] for r in rows])
lf = np.array([r['landform'] for r in rows])
relief = np.array([r['relief'] for r in rows])
pyc = np.array([r['py_class'] or '' for r in rows])
dist = np.array([r.get('district') or '' for r in rows])

print(f"范围 {scope}：有效点 {len(rows)} / {len(d['rows'])}（框内格点），"
      f"步长 {d['step_m']:.0f} m，坐向假设 {d['theta']}")
if dist.any():
    print('按区：', {k: int((dist == k).sum()) for k in sorted(set(dist)) if k})
print(f"地貌：", {k: int((lf == k).sum()) for k in sorted(set(lf))})
print(f"模式：", {k: int((mode == k).sum()) for k in sorted(set(mode))})
print(f"起伏 relief_3km：中位 {np.median(relief):.0f} m，P90 {np.percentile(relief,90):.0f} m")
print(f"平洋支干判定：", {k: int((pyc == k).sum()) for k in sorted(set(pyc))})
print()
print(f"现代版 v1.1  均 {M.mean():.3f}  SD {M.std():.3f}  P10 {np.percentile(M,10):.3f}  P90 {np.percentile(M,90):.3f}  最高 {M.max():.3f}")
print(f"葬經翼本     均 {Z.mean():.3f}  SD {Z.std():.3f}  P10 {np.percentile(Z,10):.3f}  P90 {np.percentile(Z,90):.3f}  最高 {Z.max():.3f}")
rho, p = stats.spearmanr(M, Z)
print(f"\n两套规则的排序相关 Spearman rho = {rho:.3f} (p={p:.2g})，Pearson r = {np.corrcoef(M,Z)[0,1]:.3f}")

tm = M >= np.percentile(M, 90); tz = Z >= np.percentile(Z, 90)
inter = (tm & tz).sum()
print(f"各自前 10%：现代版 {tm.sum()} 点，葬經翼 {tz.sum()} 点，重合 {inter} 点 "
      f"= {inter/tm.sum()*100:.0f}%（随机重合期望 10%）")

# 分歧最大的点
def pct(v): return v.argsort().argsort() / (len(v) - 1)
D = pct(M) - pct(Z)
print(f"\n分位差 |D| 中位 {np.median(np.abs(D)):.3f}，P90 {np.percentile(np.abs(D),90):.3f}")
for tag, idx in (('现代版更看好（前 5）', np.argsort(-D)[:5]),
                 ('葬經翼更看好（前 5）', np.argsort(D)[:5])):
    print(f'\n{tag}')
    for i in idx:
        print(f"  {lat[i]:.3f}N {lon[i]:.3f}E  现代 {M[i]:.3f}(分位{pct(M)[i]*100:.0f}%) "
              f"葬經翼 {Z[i]:.3f}(分位{pct(Z)[i]*100:.0f}%)  {lf[i]} relief={relief[i]:.0f} {pyc[i]}")

# 分歧从哪来：按地貌与支干类别看
print('\n按地貌分层的分位差均值（正＝现代版更看好）')
for k in sorted(set(lf)):
    m = lf == k
    if m.sum() < 20: continue
    print(f"  {k:<6} n={m.sum():5d}  D均 {D[m].mean():+.3f}")
print('按平洋支干判定分层')
for k in sorted(set(pyc)):
    m = pyc == k
    if m.sum() < 20: continue
    print(f"  {k:<20} n={m.sum():5d}  D均 {D[m].mean():+.3f}  现代均 {M[m].mean():.3f}  葬經翼均 {Z[m].mean():.3f}")

# ── 按行政区汇总 ────────────────────────────────────────────────
if dist.any():
    print('\n按行政区（面积＝格点数 × 步长²）')
    print(f"{'区':<7}{'点数':>6}{'面积km²':>9}{'现代均':>8}{'现代P90':>9}{'葬經翼均':>9}"
          f"{'葬經翼P90':>10}{'平原%':>7}{'支幹相扶%':>10}")
    cell = (d['step_m'] / 1000.0) ** 2
    for k in sorted(set(dist)):
        if not k: continue
        m = dist == k
        print(f"{k:<8}{m.sum():6d}{m.sum()*cell:9.0f}{M[m].mean():8.3f}"
              f"{np.percentile(M[m],90):9.3f}{Z[m].mean():9.3f}{np.percentile(Z[m],90):10.3f}"
              f"{100*(lf[m]=='平原').mean():7.0f}{100*(pyc[m]=='支幹相扶').mean():10.0f}")

    print('\n各区在全市区分布中的中位分位')
    pm = M.argsort().argsort() / (len(M) - 1)
    pz = Z.argsort().argsort() / (len(Z) - 1)
    order = sorted([k for k in set(dist) if k],
                   key=lambda k: -np.median(pm[dist == k]))
    for k in order:
        m = dist == k
        print(f"  {k:<7} 现代版 {np.median(pm[m])*100:5.1f}%   "
              f"《葬經翼》 {np.median(pz[m])*100:5.1f}%")
