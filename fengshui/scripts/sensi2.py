import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
RNG=np.random.default_rng(11)
reg=K.Mosaic('晋南豫北',range(34,37),range(112,115))
BG=json.load(open('out/bg_晋南豫北.json'))
base=[b for b in BG if 34.07<b['lat']<36.93 and 112.07<b['lon']<114.93][:200]
print(f"基准点 {len(base)}")
print(f"{'位移':>7s}{'相关 r':>9s}{'衰减后可测效应':>14s}{'需要的样本量 n':>15s}")
bs=np.array([b['score'] for b in BG]); sd=bs.std()
P=json.load(open('out/pos_晋南豫北.json')); eff=np.mean([p['score'] for p in P])-bs.mean()
print(f"（真实效应按 {eff:+.3f} 计，背景 SD {sd:.3f}）\n")
out={}
for d in [0,250,500,1000,2000,4000]:
    o,n=[],[]
    for b in base:
        if d==0: o.append(b['score']); n.append(b['score']); continue
        th=RNG.uniform(0,360)
        la=b['lat']+math.cos(math.radians(th))*d/L.M_PER_DEG_LAT
        lo=b['lon']+math.sin(math.radians(th))*d/reg.mx
        s=L.score(L.metrics(reg,la,lo))
        if s: o.append(b['score']); n.append(s['final'])
    r=float(np.corrcoef(o,n)[0,1])
    att=eff*r                                   # 位移后仍可观测的效应
    need=int(2*(1.96+0.84)**2*sd**2/max(att,1e-6)**2) if att>0 else -1
    out[d]=dict(r=r,att=att,need=need)
    print(f"{d:6d}m{r:9.3f}{att:+14.4f}{need:15d}")
json.dump(out,open('out/attenuation.json','w'),default=float)
