# -*- coding: utf-8 -*-
"""用官方名录的「类别」与「时代」重做分层 —— 轴 1 与轴 2 的正式检验。
   元数据源：维基百科「第N批全国重点文物保护单位」名录（编号第三段=官方类别码，另有时代列）。
   比 Wikidata 好得多：类别 100%、时代 98%（Wikidata 时代仅 5%）。"""
import json, glob, os, re
import numpy as np
from scipy import stats
HERE=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(HERE,'..','results','round2')
META=json.load(open('/home/user/fs/guobao_meta.json',encoding='utf8'))
def norm(n): return re.sub(r'[（(].*?[)）]|\s|·|・|　','',n)
M={norm(k):v for k,v in META.items()}

DYN=[('史前',['新石器','旧石器','石器']),('商周',['商','周','西周','东周','春秋','战国']),
     ('秦汉',['秦','汉']),('魏晋南北朝',['三国','晋','南北朝','十六国']),
     ('隋唐',['隋','唐','五代']),('宋辽金',['宋','辽','金','西夏']),
     ('元',['元']),('明',['明']),('清',['清']),('近现代',['民国','1','2'])]
def dyn_of(era):
    if not era: return None
    for d,ks in DYN:
        for k in ks:
            if era.startswith(k) or (k in era and len(k)>1): return d
    m=re.match(r'(\d{3,4})年', era)
    if m:
        y=int(m.group(1))
        return '近现代' if y>=1840 else '清' if y>=1644 else '明' if y>=1368 else '元'
    return None

P=[]
for f in sorted(glob.glob(os.path.join(R,'pos_*.json'))):
    reg=os.path.basename(f)[4:-5]
    bg=json.load(open(os.path.join(R,f'bg_{reg}.json'),encoding='utf8'))
    thr=np.percentile([x['score'] for x in bg],80); bm=np.mean([x['score'] for x in bg])
    for p in json.load(open(f,encoding='utf8')):
        m=M.get(norm(p['name']))
        P.append(dict(name=p['name'], reg=reg, score=p['score'], thr=thr, bm=bm,
                      cat=m['cat'] if m else None, era=m['era'] if m else None,
                      dyn=dyn_of(m['era']) if m else None))
n_m=sum(1 for p in P if p['cat'])
print(f"round2 正样本 {len(P)}，匹配到官方元数据 {n_m}（{n_m/len(P)*100:.0f}%）\n")

def rep(title, keyf, minn=8):
    print(f"=== {title} ===")
    print(f"{'层':<24}{'n':>5}{'效应':>8}{'落高分区%':>10}{'增益':>9}{'p':>7}")
    g={}
    for p in P:
        k=keyf(p)
        if k: g.setdefault(k,[]).append(p)
    for k,v in sorted(g.items(), key=lambda x:-len(x[1])):
        if len(v)<minn: continue
        s=np.array([x['score'] for x in v]); thr=np.mean([x['thr'] for x in v]); bm=np.mean([x['bm'] for x in v])
        hit=float((s>=thr).mean()); kk=int((s>=thr).sum())
        gn=1-0.20/hit if hit>0 else float('-inf')
        pv=stats.binomtest(kk,len(v),0.20,alternative='greater').pvalue
        print(f"{k:<24}{len(v):>5}{s.mean()-bm:+8.3f}{hit*100:9.1f}%{gn:+9.3f}{pv:7.3f}")
    print()

rep("A · 官方类别（轴 1 的正式检验）", lambda p: p['cat'])
rep("B · 朝代（轴 2 的正式检验）", lambda p: p['dyn'])
rep("C · 区 × 朝代", lambda p: f"{p['reg']}/{p['dyn']}" if p['dyn'] else None, minn=10)
