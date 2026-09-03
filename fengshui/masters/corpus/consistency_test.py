# -*- coding: utf-8 -*-
"""语料内部一致性检验：飞星格局 vs 原文断语的正负
   —— 不需要坐标，只用《沈氏玄空学·阴宅秘断》21 案自身。

   注意：这不是预测效度检验。章仲山写断语时已经排好了盘，
   所以一致是「构造上应该发生」的。本检验测的是：
   即使在作者可以让它对得上的条件下，它有多对得上。
"""
import json, re, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'audit', 'geo'))
import pipeline as P
from scipy import stats
import numpy as np

POS = ['科甲','状元','探花','大旺','旺财','旺丁','富','贵','大发','连绵','兴家','财丁两旺']
NEG = ['败','退财','损丁','绝','寡','夭','讼','血证','淫','盗','伤','丁稀','少丁','不利','凶']
RANK = {'旺山旺向': 3, '双星到向': 2, '双星到坐': 2, '上山下水': 1}

cases = json.load(open(os.path.join(HERE, 'yinzhai_parsed.json'), encoding='utf8'))
r, s, rows = [], [], []
for c in cases:
    g = P.chart(c['yun'], c['zuo'], 'std')['ge']
    m = re.search(r'仲山曰[：:“"]?(.{0,300})', c['text'], re.S)
    d = m.group(1) if m else c['text'][:300]
    p = sum(d.count(k) for k in POS); n = sum(d.count(k) for k in NEG)
    pol = 0 if p == n else (1 if p > n else -1)
    r.append(RANK.get(g, 2)); s.append(pol)
    rows.append((c['name'][:16], c['zuo'], c['xiang'], c['yun'], g, pol))
r, s = np.array(r), np.array(s)

print(f"{'案':<18}{'坐':<3}{'向':<3}{'运':>3}  {'格局':<9}断语")
for nm, z, x, y, g, pol in rows:
    print(f"{nm:<18}{z:<3}{x:<3}{y:>3}  {g:<9}{'正' if pol>0 else ('负' if pol<0 else '平')}")

print(f"\nn = {len(r)}")
for k, v in (('旺山旺向', 3), ('双星到向/到坐', 2), ('上山下水', 1)):
    m = s[r == v]
    print(f"  {k:<16} n={len(m):2d}  正{int((m>0).sum())} 平{int((m==0).sum())} 负{int((m<0).sum())}"
          f"  均值 {m.mean():+.2f}")
rho, p = stats.spearmanr(r, s)
u, pu = stats.mannwhitneyu(s[r == 3], s[r == 1], alternative='greater')
print(f"\nSpearman rho = {rho:+.3f}, p = {p:.3f}")
print(f"旺山旺向 vs 上山下水  Mann-Whitney U = {u:.1f}, 单尾 p = {pu:.3f}")
