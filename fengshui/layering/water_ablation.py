# -*- coding: utf-8 -*-
"""轴 7 的直接检验：剔除 water 与 water_gate（其余权重按比例归一），看各区增益变化。
   动机：实测二证明古代都邑的现代水系代理已失真，而平原模式下水类占 48% 权重。

   注意：round2 的 faults 字段只存凶格**名称**不存折减值，无法忠实重建最终分
   （重建 vs 存储 corr=0.84）。故本检验一律用**不含凶格折减的基础分**，
   两种条件下口径一致，比较有效；但绝对值与 results/ 里的存储分不可直接对照。"""
import json, glob, os
import numpy as np
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'results', 'round2')
W_MOUNT = dict(water=.24, water_gate=.09, mingtang=.18, xuanwu=.15, hulong=.11, xiangbei=.12, zangfeng=.11)
W_PLAIN = dict(water=.34, water_gate=.14, mingtang=.22, xuanwu=.08, hulong=.06, xiangbei=.13, zangfeng=.03)

def base(x, drop=()):
    W = dict(W_PLAIN if x.get('mode') == 'plain' else W_MOUNT)
    for d in drop: W.pop(d, None)
    t = sum(W.values())
    return sum(W[k] * x['comp'].get(k, 0) for k in W) / t

def gain(P, B, drop):
    b = np.array([base(x, drop) for x in B]); s = np.array([base(x, drop) for x in P])
    thr = np.percentile(b, 80); hit = float((s >= thr).mean()); k = int((s >= thr).sum())
    g = 1 - 0.20/hit if hit > 0 else float('-inf')
    return s.mean()-b.mean(), hit, g, stats.binomtest(k, len(s), 0.20, alternative='greater').pvalue

print("基础分（不含凶格折减），两种条件口径一致")
print(f"{'区':<10}{'条件':>6}{'效应':>8}{'落高分区%':>10}{'增益':>9}{'p':>7}")
for f in sorted(glob.glob(os.path.join(R, 'pos_*.json'))):
    reg = os.path.basename(f)[4:-5]
    P = json.load(open(f, encoding='utf8'))
    B = json.load(open(os.path.join(R, f'bg_{reg}.json'), encoding='utf8'))
    for tag, drop in (('含水', ()), ('去水', ('water', 'water_gate'))):
        e, h, g, pv = gain(P, B, drop)
        print(f"{reg:<10}{tag:>6}{e:+8.3f}{h*100:9.1f}%{g:+9.3f}{pv:7.3f}")
    print()
