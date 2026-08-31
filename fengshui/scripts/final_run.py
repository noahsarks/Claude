import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L
RNG = np.random.default_rng(20260831)
TARGETS = [
    ("明十三陵·长陵",   40.2967, 116.2331, "山地·陵", "我给的初值"),
    ("北京故宫·太和殿", 39.9151, 116.3972, "平原·宫", "我给的初值"),
    ("清东陵·孝陵",     40.1857, 117.6390, "山地·陵", "已按维基修正(原值偏北1.55km)"),
    ("秦始皇陵·封土",   34.3814, 109.2533, "山前·陵", "我给的初值"),
    ("唐乾陵·北峰玄宫", 34.5815, 108.2129, "因山为陵", "按DEM峰顶修正(1045.7m≈文献1047.9m)"),
]
def quick(reg, lat, lon):
    r0, c0 = reg.rc(lat, lon); r0, c0 = int(r0), int(c0)
    kr = int(3000/(L.RES*L.M_PER_DEG_LAT)); kc = int(3000/(L.RES*reg.mx))
    if r0-kr<0 or c0-kc<0 or r0+kr>=reg.arr.shape[0] or c0+kc>=reg.arr.shape[1]: return None
    w = reg.arr[r0-kr:r0+kr, c0-kc:c0+kc]
    if np.isnan(w).mean() > .2: return None
    return float(reg.arr[r0,c0]), float(np.nanmax(w)-np.nanmin(w))
def sample_pts(reg, lat, lon, n, matched, h0, rel0):
    out, t = [], 0; mg = 6200
    while len(out) < n and t < n*60:
        t += 1
        d = math.sqrt(RNG.uniform(5000**2, 25000**2)); b = RNG.uniform(0,360)
        la = lat + math.cos(math.radians(b))*d/L.M_PER_DEG_LAT
        lo = lon + math.sin(math.radians(b))*d/reg.mx
        rr, cc = reg.rc(la, lo)
        if not (mg/(L.RES*L.M_PER_DEG_LAT) < rr < reg.arr.shape[0]-mg/(L.RES*L.M_PER_DEG_LAT)): continue
        if not (mg/(L.RES*reg.mx) < cc < reg.arr.shape[1]-mg/(L.RES*reg.mx)): continue
        q = quick(reg, la, lo)
        if q is None: continue
        if matched and (abs(q[0]-h0) > 150 or not (.6*rel0 <= q[1] <= 1.7*rel0)): continue
        out.append((la, lo))
    return out
rep=[]
for name, lat, lon, kind, note in TARGETS:
    reg = L.Region(name, lat, lon, pad=.33)
    M = L.metrics(reg, lat, lon); S = L.score(M)
    row = dict(name=name, kind=kind, note=note, lat=lat, lon=lon, final=S["final"],
               mode=S["mode"], faults=list(S["faults"]), comp=S["components"], m=M)
    for tag, matched in (("naive",False),("matched",True)):
        pts = sample_pts(reg, lat, lon, 180, matched, M["h0"], M["relief_3km"])
        sc = np.array([s["final"] for s in (L.score(L.metrics(reg,a,b)) for a,b in pts) if s])
        row[tag] = dict(n=len(sc), pct=float((sc<S["final"]).mean()*100),
                        mean=float(sc.mean()), p90=float(np.percentile(sc,90)))
    rep.append(row)
    print(f"{name:16s} {kind:8s} final={S['final']:.3f} naive={row['naive']['pct']:5.1f}% "
          f"matched={row['matched']['pct']:5.1f}% (n={row['matched']['n']}) faults={row['faults']}", flush=True)
    del reg
json.dump(rep, open('/home/user/fs/out/final.json','w'), ensure_ascii=False, indent=1, default=float)
print("saved")
