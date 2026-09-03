# -*- coding: utf-8 -*-
"""检验「引擎得分主要在测地形起伏」这一混杂假设。
   两步：① corr(score, relief) ② 按 relief 匹配后重算增益。
   结论：两步都不支持该假设——R²=0.10，匹配后增益基本不变。"""
import json, glob, os
import numpy as np
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', 'results', 'round2')

print(f"{'区':<10}{'corr(score,relief)':>20}{'corr(score,h)':>15}")
allb = []
for f in sorted(glob.glob(os.path.join(R, 'bg_*.json'))):
    reg = os.path.basename(f)[3:-5]
    b = json.load(open(f, encoding='utf8')); allb += b
    s = np.array([x['score'] for x in b]); r = np.array([x.get('relief', 0) for x in b])
    h = np.array([x.get('h', 0) for x in b])
    print(f"{reg:<10}{stats.pearsonr(s,r)[0]:>20.3f}{stats.pearsonr(s,h)[0]:>15.3f}")
s = np.array([x['score'] for x in allb]); r = np.array([x.get('relief', 0) for x in allb])
rho = stats.pearsonr(s, r)
print(f"\n三区合并 corr = {rho[0]:.3f} (p={rho[1]:.1e})，R² = {rho[0]**2:.2f}"
      f" —— 起伏只解释得分方差的 {rho[0]**2*100:.0f}%")

print("\n按 relief 匹配后的增益（每个正样本配同区内 relief 最接近的 20 个背景点）")
print(f"{'区':<10}{'n正':>5}{'原增益':>9}{'匹配后':>9}{'p':>8}")
for f in sorted(glob.glob(os.path.join(R, 'pos_*.json'))):
    reg = os.path.basename(f)[4:-5]
    P = json.load(open(f, encoding='utf8'))
    B = json.load(open(os.path.join(R, f'bg_{reg}.json'), encoding='utf8'))
    bs = np.array([x['score'] for x in B]); br = np.array([x.get('relief', 0) for x in B])
    thr0 = np.percentile(bs, 80)
    hit0 = np.mean([p['score'] >= thr0 for p in P]); g0 = 1 - 0.20/hit0 if hit0 else float('-inf')
    k = sum(1 for p in P
            if p['score'] >= np.percentile(bs[np.argsort(np.abs(br - p.get('relief', 0)))[:20]], 80))
    n = len(P); hit = k/n; g = 1 - 0.20/hit if hit else float('-inf')
    pv = stats.binomtest(k, n, 0.20, alternative='greater').pvalue
    print(f"{reg:<10}{n:>5}{g0:+9.3f}{g:+9.3f}{pv:8.3f}")
print("""
注：区级上「正样本-背景起伏差」的符号与增益符号完全对应（-153/-106/+28 对 -0.171/-0.743/+0.300），
但那是 n=3 的对应，三个点上任何单调量都能对上。点级检验一做即不成立。""")
