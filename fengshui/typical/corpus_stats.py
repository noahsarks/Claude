# -*- coding: utf-8 -*-
"""按 works.yaml 的分类统计语料体量：技术 vs 批判，托名 vs 年代确定。

立这个统计的原因：做编年之前得先知道「可以断代的部分占多少」。
结果是本项目关于文献层的最重要一条结构性事实。
"""
import os, re, yaml
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(os.path.dirname(HERE), 'masters', 'corpus', 'gjtsjc')
W = yaml.safe_load(open(os.path.join(HERE, 'works.yaml'), encoding='utf8'))['works']

def body(n):
    """去掉页眉、目录、维基导航，留正文近似字数。"""
    t = open(os.path.join(G, f'{n}.txt'), encoding='utf8').read()
    i = t.find('[编辑]')
    t = t[i:] if i > 0 else t
    t = re.sub(r'\[编辑\]|←.*|→|姊妹计划.*|欽定古今圖書集成.*|博物彙編.*', '', t)
    return len(re.findall(r'[一-鿿]', t))

chars = {n: body(n) for n in range(651, 681)}
# 卷 655 与 665、666、667 有多书共卷，按卷平摊到该卷所列各书
juan_books = defaultdict(list)
for w in W:
    for j in w['卷']:
        juan_books[j].append(w)

tot = defaultdict(int); tot_rel = defaultdict(int)
for j, ws in juan_books.items():
    share = chars[j] / len(ws)
    for w in ws:
        tot[w['性质']] += share
        tot_rel[(w['性质'], w['年代可靠性'])] += share

grand = sum(tot.values())
print(f"语料正文汉字总数 {grand:,.0f}（30 卷）\n")
print(f"{'性质':<6}{'字数':>10}{'占比':>8}")
for k, v in sorted(tot.items(), key=lambda x: -x[1]):
    print(f"{k:<7}{v:10,.0f}{v/grand*100:7.1f}%")

print(f"\n{'性质':<6}{'年代可靠性':<20}{'字数':>10}{'占该性质':>9}")
for (a, b), v in sorted(tot_rel.items(), key=lambda x: (x[0][0], -x[1])):
    print(f"{a:<7}{b:<22}{v:10,.0f}{v/tot[a]*100:8.1f}%")

t_sure = sum(v for (a, b), v in tot_rel.items() if a == '技术' and b == '确定')
print(f"\n技术文献里年代确定的：{t_sure:,.0f} 字，占技术文献 {t_sure/tot['技术']*100:.1f}%")
print(f"批判文献里年代确定的：100%（7/7 篇，作者生卒俱可考）")
