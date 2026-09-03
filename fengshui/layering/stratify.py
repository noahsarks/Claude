# -*- coding: utf-8 -*-
"""按对象类型分层重算增益 —— 检验「对象混用是否是效应量低的主因」。
   数据：results/round2/{pos,bg}_*.json（三区各 3000 背景点 + 正样本）"""
import json, os, glob
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', 'results', 'round2')

CLS = [('阴宅', ['墓','陵','冢']),
       ('宗教', ['寺','庙','观','塔','祠','庵','宫']),
       ('城址', ['城','遗址','故城','都']),
       ('阳宅', ['故居','宅','府','署','楼','会馆','书院']),
       ('工程', ['桥','窑','厂','矿','站','闸','堰','渠','坝'])]

def cls_of(name):
    for c, ks in CLS:
        if any(k in name for k in ks):
            return c
    return '其他'

rows = {}
for f in sorted(glob.glob(os.path.join(R, 'pos_*.json'))):
    reg = os.path.basename(f)[4:-5]
    pos = json.load(open(f, encoding='utf8'))
    bg = json.load(open(os.path.join(R, f'bg_{reg}.json'), encoding='utf8'))
    b = np.array([x['score'] for x in bg])
    thr = np.percentile(b, 80)          # 背景上四分之一 → I+II 区（面积 20%）
    for p in pos:
        rows.setdefault(cls_of(p['name']), []).append((p['score'], thr, b.mean()))

print(f"{'层':<6}{'n':>5}{'均分':>8}{'背景均分':>9}{'效应':>8}{'落高分区%':>10}{'增益':>8}{'p':>8}")
allp = []
for c, v in sorted(rows.items(), key=lambda x: -len(x[1])):
    s = np.array([x[0] for x in v]); thr = v[0][1]; bm = np.mean([x[2] for x in v])
    hit = float((s >= thr).mean())
    gain = 1 - 0.20/hit if hit > 0 else float('-inf')
    k = int((s >= thr).sum()); n = len(s)
    p = stats.binomtest(k, n, 0.20, alternative='greater').pvalue
    allp.append((c, n, s.mean()-bm, hit, gain, p))
    print(f"{c:<6}{n:>5}{s.mean():8.3f}{bm:9.3f}{s.mean()-bm:+8.3f}{hit*100:9.1f}%{gain:+8.3f}{p:8.3f}")

s_all = np.array([x[0] for v in rows.values() for x in v])
b_all = np.mean([x[2] for v in rows.values() for x in v])
thr_all = np.mean([x[1] for v in rows.values() for x in v])
hit = float((s_all >= thr_all).mean())
print(f"{'合计':<6}{len(s_all):>5}{s_all.mean():8.3f}{b_all:9.3f}{s_all.mean()-b_all:+8.3f}"
      f"{hit*100:9.1f}%{1-0.20/hit:+8.3f}")
print("""
判读要点：
  「阴宅」层是规则的**对象匹配**层——全部 16 条规则都出自阴宅文献。
  其余各层是**对象不匹配**层，规则本不该用于它们。
  若对象混用是主因，阴宅层的效应应显著高于其余层。""")
