"""上限测试：人工核准精度(±100m)下，指标本身稳不稳。"""
import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L
RNG=np.random.default_rng(3)
PTS=[("明十三陵·长陵",40.2967,116.2331),("北京故宫·太和殿",39.9151,116.3972),
     ("清东陵·孝陵",40.1857,117.6390),("秦始皇陵·封土",34.3814,109.2533),
     ("唐乾陵·北峰玄宫",34.5815,108.2129)]
print(f"{'点位':18s}{'基准分':>8s}{'±100m 均值':>11s}{'SD':>8s}{'极差':>8s}")
res={}
for nm,la,lo in PTS:
    reg=L.Region(nm,la,lo)
    b=L.score(L.metrics(reg,la,lo))['final']
    vs=[]
    for _ in range(50):
        d=RNG.uniform(0,100); th=RNG.uniform(0,360)
        s=L.score(L.metrics(reg,la+math.cos(math.radians(th))*d/L.M_PER_DEG_LAT,
                                lo+math.sin(math.radians(th))*d/reg.mx))
        if s: vs.append(s['final'])
    a=np.array(vs); res[nm]=dict(base=b,mean=float(a.mean()),sd=float(a.std()),
                                 lo=float(a.min()),hi=float(a.max()))
    print(f"{nm:18s}{b:8.3f}{a.mean():11.3f}{a.std():8.3f}{a.max()-a.min():8.3f}",flush=True)
    del reg
sd=np.mean([v['sd'] for v in res.values()])
print(f"\n±100 m 抖动的平均 SD = {sd:.3f}")
print(f"对比：要测的效应 0.043，背景 SD 0.120")
print(f"→ 人工核准精度下的噪声占效应的 {sd/0.043*100:.0f}%")
json.dump(res,open('out/ceiling.json','w'),ensure_ascii=False,indent=1,default=float)
