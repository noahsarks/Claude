# -*- coding: utf-8 -*-
"""跨两百年回归测试
   用本项目已验证的 216 局挨星实现（audit/geo/pipeline.py 的 'std' 规则），
   复算《沈氏玄空学·阳宅秘断》诸案，与原文断语比对。

   原文来源：shen/*.txt（章仲山《宅斷》原文 + 沈竹礽注 + 王则先「则先谨按」）
   沈竹礽 1849-1906、王则先 民国 —— 原文与按语属公有领域。

   用法：python3 regress_qing.py    （需 audit/geo/pipeline.py 在 sys.path）
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'audit', 'geo'))
import pipeline as P

# (案名, 坐, 向, 运, 原文中可判读的盘面语, 期望格局)
# 「用替卦」者单列，本实现只做下卦，不参与比对
XIAGUA = [
    ('陶姓宅  丑山未向',     '丑','未',5, '旺星到向也；【按】五运丑山未向为旺山旺向', '旺山旺向'),
    ('会稽任宅 子午兼壬丙',  '子','午',7, '双七到后，后有大河故也',                   '双星到坐'),
    ('会稽章宅 子午兼癸丁',  '子','午',7, '双七临坎；八运财大退，坤方无水…名为上山',  '双星到坐'),
    ('张村丁宅 子午兼癸丁',  '子','午',7, '此屋向星上山，后无水，本主不吉',           '双星到坐'),
    ('胡宅   甲山庚向',      '甲','庚',7, '山颠水倒，本主不吉',                       '上山下水'),
    ('某宅   申寅兼坤艮',    '申','寅',7, '向上双七、七为少女',                       '双星到向'),
]
TIGUA = [
    ('某宅 壬丙兼亥巳 五运', '此局用变卦故七二入中…此用替卦之法也'),
    ('某宅 辛乙兼戊辰 五运', '此局用变卦故二七入中…亦用替卦法也'),
]

ok = 0
print("下卦诸案（本实现覆盖）")
print(f"{'案':<22}{'运':>3}  {'本实现':<8}{'原文':<8} {'':<2} 原文语")
for name, z, x, y, quote, exp in XIAGUA:
    got = P.chart(y, z, 'std')['ge']
    m = (got == exp); ok += m
    print(f"{name:<22}{y:>3}  {got:<8}{exp:<8} {'✓' if m else '✗'}  {quote}")
print(f"\n下卦 {ok}/{len(XIAGUA)} 一致")
print("\n替卦诸案（本实现不做替卦，原文自己标明用替，故不参与比对）")
for name, quote in TIGUA:
    print(f"  {name:<24} {quote}")
