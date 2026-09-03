# -*- coding: utf-8 -*-
"""在这三个点各自实测局地噪声：±100 m 与 ±1 km 随机位移下得分的标准差。
   噪声与地形相关（平坦三角洲低、盆地边缘高），不能照搬黄土高原的数字。"""
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
rng=np.random.default_rng(7)
SITES=[('上海中心大厦',31.23559,121.50127),('金茂大厦',31.23726,121.50139),('台北101',25.03395,121.56461)]
N=40
print(f"{'点':<14}{'基准':>7}{'±100m SD':>10}{'±1km SD':>9}{'±1km 极差':>10}")
out={}
for n,la,lo in SITES:
    rows=range(int(la),int(la)+1); cols=range(int(lo),int(lo)+1)
    reg=K.Mosaic(n,rows,cols)
    base=L.score(L.metrics(reg,la,lo))['final']
    res={}
    for tag,r in (('100m',100.0),('1km',1000.0)):
        v=[]
        for _ in range(N):
            th=rng.uniform(0,2*math.pi); rr=r*math.sqrt(rng.uniform())
            dla=rr*math.cos(th)/110540; dlo=rr*math.sin(th)/(111320*math.cos(math.radians(la)))
            try: v.append(L.score(L.metrics(reg,la+dla,lo+dlo))['final'])
            except Exception: pass
        res[tag]=np.array(v)
    out[n]=dict(base=base, sd100=float(res['100m'].std()), sd1k=float(res['1km'].std()),
                rng1k=float(res['1km'].max()-res['1km'].min()))
    print(f"{n:<14}{base:7.3f}{res['100m'].std():10.3f}{res['1km'].std():9.3f}"
          f"{res['1km'].max()-res['1km'].min():10.3f}")
json.dump(out, open('dem_noise.json','w'), ensure_ascii=False, indent=1)
