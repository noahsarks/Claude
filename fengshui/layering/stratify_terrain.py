# -*- coding: utf-8 -*-
"""轴 11 的第一个直接检验：按**地形类型**分层，看是否比按对象分层解释力更强。
   用已有字段 mode(mountain/plain) 与 relief（局地起伏），无需新数据。"""
import json, glob, os
import numpy as np
from scipy import stats
HERE=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(HERE,'..','results','round2')

def load():
    P,B=[],[]
    for f in sorted(glob.glob(os.path.join(R,'pos_*.json'))):
        reg=os.path.basename(f)[4:-5]
        pos=json.load(open(f,encoding='utf8')); bg=json.load(open(os.path.join(R,f'bg_{reg}.json'),encoding='utf8'))
        for p in pos: p['reg']=reg; P.append(p)
        for b in bg: b['reg']=reg; B.append(b)
    return P,B
P,B=load()

def report(title, keyf):
    print(f"\n=== {title} ===")
    print(f"{'层':<16}{'n正':>5}{'n背':>6}{'正均分':>8}{'背均分':>8}{'效应':>8}{'落高分区%':>10}{'增益':>8}{'p':>7}")
    keys=sorted({keyf(x) for x in P}|{keyf(x) for x in B}, key=str)
    for k in keys:
        pb=[x['score'] for x in B if keyf(x)==k]
        pp=[x['score'] for x in P if keyf(x)==k]
        if len(pp)<5 or len(pb)<50: continue
        b=np.array(pb); s=np.array(pp); thr=np.percentile(b,80)
        hit=float((s>=thr).mean()); kk=int((s>=thr).sum()); n=len(s)
        g=1-0.20/hit if hit>0 else float('-inf')
        pv=stats.binomtest(kk,n,0.20,alternative='greater').pvalue
        print(f"{str(k):<16}{n:>5}{len(b):>6}{s.mean():8.3f}{b.mean():8.3f}{s.mean()-b.mean():+8.3f}{hit*100:9.1f}%{g:+8.3f}{pv:7.3f}")

report("A · 按山地/平原（引擎自身的 mode 判定）", lambda x: x.get('mode','?'))

def rb(x):
    r=x.get('relief',0)
    return '起伏<50m' if r<50 else '50-150m' if r<150 else '150-300m' if r<300 else '≥300m'
report("B · 按局地起伏分档", rb)

report("C · 按区", lambda x: x['reg'])

print("""
判读：
  按对象分层（stratify.py）后，同一层三区符号互相矛盾，说明对象不是主因。
  若按地形类型分层能让各层内部一致、且层间差异明显，则轴 11（地域/地貌）得到支持。""")
