"""v1 vs v2 规则的匹配对照 A/B 检验（同一批对照点，同一协议）。"""
import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as V2, luantou_v1 as V1
RNG=np.random.default_rng(20260831)
PTS=[("明十三陵·长陵",40.2967,116.2331),("北京故宫·太和殿",39.9151,116.3972),
     ("清东陵·孝陵",40.1857,117.6390),("秦始皇陵·封土",34.3814,109.2533),
     ("唐乾陵·北峰玄宫",34.5815,108.2129)]
N=150
def quick(reg,la,lo):
    r0,c0=reg.rc(la,lo); r0,c0=int(r0),int(c0)
    kr=int(3000/(V2.RES*V2.M_PER_DEG_LAT)); kc=int(3000/(V2.RES*reg.mx))
    if r0-kr<0 or c0-kc<0 or r0+kr>=reg.arr.shape[0] or c0+kc>=reg.arr.shape[1]: return None
    w=reg.arr[r0-kr:r0+kr,c0-kc:c0+kc]
    if np.isnan(w).mean()>.2: return None
    return float(reg.arr[r0,c0]), float(np.nanmax(w)-np.nanmin(w))
rows=[]
print(f"{'点位':16s}{'v1 分':>7s}{'v1 %':>7s}{'v2 分':>7s}{'v2 %':>7s}{'变化':>8s}")
for nm,la,lo in PTS:
    reg=V2.Region(nm,la,lo,pad=.33)
    q=quick(reg,la,lo); h0,rel0=q
    pts=[];t=0
    while len(pts)<N and t<N*60:
        t+=1
        d=math.sqrt(RNG.uniform(5000**2,25000**2)); b=RNG.uniform(0,360)
        a=la+math.cos(math.radians(b))*d/V2.M_PER_DEG_LAT
        o=lo+math.sin(math.radians(b))*d/reg.mx
        rr,cc=reg.rc(a,o); mg=6200
        if not (mg/(V2.RES*V2.M_PER_DEG_LAT)<rr<reg.arr.shape[0]-mg/(V2.RES*V2.M_PER_DEG_LAT)): continue
        if not (mg/(V2.RES*reg.mx)<cc<reg.arr.shape[1]-mg/(V2.RES*reg.mx)): continue
        z=quick(reg,a,o)
        if z is None or abs(z[0]-h0)>150 or not (.6*rel0<=z[1]<=1.7*rel0): continue
        pts.append((a,o))
    r={}
    for tag,MOD in (('v1',V1),('v2',V2)):
        tv=MOD.score(MOD.metrics(reg,la,lo))['final']
        cs=np.array([s['final'] for s in (MOD.score(MOD.metrics(reg,a,o)) for a,o in pts) if s])
        r[tag]=(tv,float((cs<tv).mean()*100),len(cs))
    rows.append(dict(name=nm,n=len(pts),v1=r['v1'],v2=r['v2']))
    print(f"{nm:16s}{r['v1'][0]:7.3f}{r['v1'][1]:7.1f}{r['v2'][0]:7.3f}{r['v2'][1]:7.1f}{r['v2'][1]-r['v1'][1]:+8.1f}",flush=True)
    del reg
json.dump(rows,open('out/ab.json','w'),ensure_ascii=False,indent=1,default=float)
v1m=np.mean([r['v1'][1] for r in rows]); v2m=np.mean([r['v2'][1] for r in rows])
print(f"\n平均百分位  v1 {v1m:.1f}%  →  v2 {v2m:.1f}%")
print(f"陵墓四点(排除故宫) v1 {np.mean([r['v1'][1] for r in rows if '故宫' not in r['name']]):.1f}%"
      f"  →  v2 {np.mean([r['v2'][1] for r in rows if '故宫' not in r['name']]):.1f}%")
