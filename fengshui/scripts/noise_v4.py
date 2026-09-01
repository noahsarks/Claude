"""v0.3 vs v0.4 噪声对比：①±100m 上限测试 ②位移衰减曲线。"""
import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs')
import luantou as V4, luantou_v3 as V3, kvamme as K
RNG=np.random.default_rng(3)
PTS=[("长陵",40.2967,116.2331),("故宫",39.9151,116.3972),("孝陵",40.1857,117.6390),
     ("秦陵",34.3814,109.2533),("乾陵",34.5815,108.2129)]
print("① 上限测试（±100 m 抖动 50 次的分数 SD）")
print(f"{'点位':8s}{'v0.3 SD':>10s}{'v0.4 SD':>10s}{'降幅':>9s}")
sd3,sd4=[],[]
for nm,la,lo in PTS:
    reg=V4.Region(nm,la,lo)
    off=[(RNG.uniform(0,100),RNG.uniform(0,360)) for _ in range(50)]
    r={}
    for tag,MOD in (('3',V3),('4',V4)):
        v=[]
        for d,th in off:
            s=MOD.score(MOD.metrics(reg,la+math.cos(math.radians(th))*d/V4.M_PER_DEG_LAT,
                                        lo+math.sin(math.radians(th))*d/reg.mx))
            if s: v.append(s['final'])
        r[tag]=float(np.std(v))
    sd3.append(r['3']); sd4.append(r['4'])
    print(f"{nm:8s}{r['3']:10.4f}{r['4']:10.4f}{(r['4']-r['3'])/max(r['3'],1e-9)*100:8.0f}%")
    del reg
print(f"{'平均':8s}{np.mean(sd3):10.4f}{np.mean(sd4):10.4f}{(np.mean(sd4)-np.mean(sd3))/np.mean(sd3)*100:8.0f}%")

print("\n② 位移衰减（晋南豫北 200 点，位移前后分数相关 r）")
reg=K.Mosaic('晋南豫北',range(34,37),range(112,115))
BG=json.load(open('out/bg_晋南豫北.json'))
base=[b for b in BG if 34.07<b['lat']<36.93 and 112.07<b['lon']<114.93][:200]
RNG2=np.random.default_rng(11)
print(f"{'位移':>7s}{'v0.3 r':>10s}{'v0.4 r':>10s}")
res={}
for d in [250,500,1000,2000]:
    draws=[(RNG2.uniform(0,360)) for _ in base]
    rr={}
    for tag,MOD in (('3',V3),('4',V4)):
        o,n=[],[]
        for b,th in zip(base,draws):
            b0=MOD.score(MOD.metrics(reg,b['lat'],b['lon']))
            s=MOD.score(MOD.metrics(reg,b['lat']+math.cos(math.radians(th))*d/V4.M_PER_DEG_LAT,
                                        b['lon']+math.sin(math.radians(th))*d/reg.mx))
            if b0 and s: o.append(b0['final']); n.append(s['final'])
        rr[tag]=float(np.corrcoef(o,n)[0,1])
    res[d]=rr
    print(f"{d:6d}m{rr['3']:10.3f}{rr['4']:10.3f}",flush=True)
json.dump(dict(sd_v3=float(np.mean(sd3)),sd_v4=float(np.mean(sd4)),atten=res),
          open('out/noise_v4.json','w'),indent=1,default=float)
