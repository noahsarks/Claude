"""位移敏感性：把点随机平移 d 米，看分数变化有多大。
   若 1.3 km 位移造成的分数扰动 >> 正样本与背景的分差，则大样本检验测的是坐标质量，不是规则。"""
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
RNG=np.random.default_rng(7)
reg=K.Mosaic('晋南豫北',range(34,37),range(112,115))
BG=json.load(open('out/bg_晋南豫北.json'))
base=[b for b in BG if 34.06<b['lat']<36.94 and 112.06<b['lon']<114.94][:120]
print(f"基准点 {len(base)} 个")
DS=[250,500,1000,2000,4000]
res={}
for d in DS:
    diff=[]
    for b in base:
        th=RNG.uniform(0,360)
        la=b['lat']+math.cos(math.radians(th))*d/L.M_PER_DEG_LAT
        lo=b['lon']+math.sin(math.radians(th))*d/reg.mx
        s=L.score(L.metrics(reg,la,lo))
        if s: diff.append(abs(s['final']-b['score']))
    res[d]=diff
    a=np.array(diff)
    print(f"  位移 {d:5d} m: |Δ分数| 中位 {np.median(a):.3f}  均值 {a.mean():.3f}  P90 {np.percentile(a,90):.3f}  n={len(a)}",flush=True)
json.dump({str(k):v for k,v in res.items()},open('out/sensitivity.json','w'))
# 参考量级
P=json.load(open('out/pos_晋南豫北.json'))
bs=np.array([b['score'] for b in BG]); ps=np.array([p['score'] for p in P])
print(f"\n参考：正样本均分 {ps.mean():.3f} − 背景均分 {bs.mean():.3f} = {ps.mean()-bs.mean():+.3f}")
print(f"      背景分数标准差 {bs.std():.3f}")
