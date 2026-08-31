import json, math
R=json.load(open('guobao.json'))
# 标准 GCJ-02 变换（用于把 WGS84 点推到 GCJ-02，反向用迭代）
A=6378245.0; EE=0.00669342162296594323
def _tl(x,y):
    r=-100+2*x+3*y+0.2*y*y+0.1*x*y+0.2*math.sqrt(abs(x))
    r+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    r+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
    r+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    return r
def _tg(x,y):
    r=300+x+2*y+0.1*x*x+0.1*x*y+0.1*math.sqrt(abs(x))
    r+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    r+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
    r+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    return r
def wgs2gcj(lat,lon):
    dlat=_tl(lon-105,lat-35); dlon=_tg(lon-105,lat-35)
    rl=lat/180*math.pi; m=1-EE*math.sin(rl)**2; sm=math.sqrt(m)
    dlat=(dlat*180)/((A*(1-EE))/(m*sm)*math.pi)
    dlon=(dlon*180)/(A/sm*math.cos(rl)*math.pi)
    return lat+dlat, lon+dlon
def gcj2wgs(lat,lon):
    la,lo=lat,lon
    for _ in range(6):
        g=wgs2gcj(la,lo); la+=lat-g[0]; lo+=lon-g[1]
    return la,lo
def d_m(a,b):
    return math.hypot((a[0]-b[0])*110540,(a[1]-b[1])*110540*math.cos(math.radians(a[0])))

TRUTH=[("故宫",39.9151,116.3972,["故宫","紫禁城"]),
       ("明十三陵",40.2967,116.2331,["十三陵","明十三陵"]),
       ("乾陵",34.5815,108.2129,["乾陵"]),
       ("秦始皇陵",34.3814,109.2533,["秦始皇陵"]),
       ("清东陵",40.1857,117.6390,["清东陵"])]
print(f"{'点':10s} {'Wikidata名':22s} {'原样距真值':>10s} {'当GCJ转WGS后':>12s}")
tot_raw=[];tot_cv=[]
for nm,la,lo,keys in TRUTH:
    best=None
    for r in R:
        if any(k in r['name'] for k in keys):
            d=d_m((la,lo),(r['lat'],r['lon']))
            if best is None or d<best[0]: best=(d,r)
    if not best: print(f"{nm:10s} 未找到"); continue
    d0,r=best
    w=gcj2wgs(r['lat'],r['lon']); d1=d_m((la,lo),w)
    tot_raw.append(d0); tot_cv.append(d1)
    print(f"{nm:10s} {r['name'][:20]:22s} {d0:9.0f}m {d1:11.0f}m")
print()
import statistics as st
print(f"中位数  原样 {st.median(tot_raw):.0f} m   转换后 {st.median(tot_cv):.0f} m")
