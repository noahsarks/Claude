import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L
RNG = np.random.default_rng(20260831)
# theta_back = 指向靠山的方位；史载坐向：坐北朝南 → 0°，秦陵背骊山(南) → 180°
TARGETS = [
    ("明十三陵·长陵",   40.2967, 116.2331,   0.0, "坐北朝南，背天寿山", "山地·陵"),
    ("北京故宫·太和殿", 39.9151, 116.3972,   0.0, "坐北朝南，中轴线",   "平原·宫"),
    ("清东陵·孝陵",     40.1857, 117.6390,   0.0, "坐北朝南，背昌瑞山", "山地·陵"),
    ("秦始皇陵·封土",   34.3814, 109.2533, 180.0, "背骊山(南)面渭水",   "山前·陵"),
    ("唐乾陵·北峰玄宫", 34.5815, 108.2129,   0.0, "因山为陵，神道向南", "因山为陵"),
]
THETAS = np.arange(0, 360, 45.0)
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
def best_score(reg, la, lo):
    best = None
    for th in THETAS:
        s = L.score(L.metrics(reg, la, lo, theta_deg=th))
        if s and (best is None or s["final"] > best["final"]): best = s
    return best
rep = []
for name, lat, lon, th, why, kind in TARGETS:
    reg = L.Region(name, lat, lon, pad=.33)
    Mh = L.metrics(reg, lat, lon, theta_deg=th); Sh = L.score(Mh)     # 史载坐向
    Ma = L.metrics(reg, lat, lon);               Sa = L.score(Ma)     # 自动坐向
    row = dict(name=name, kind=kind, why=why, lat=lat, lon=lon,
               hist=dict(theta=th, final=Sh["final"], mode=Sh["mode"],
                         faults=list(Sh["faults"]), comp=Sh["components"]),
               auto=dict(theta=Ma["theta_back"], final=Sa["final"], faults=list(Sa["faults"])),
               m=Mh)
    for tag, matched in (("naive", False), ("matched", True)):
        pts = sample_pts(reg, lat, lon, 150, matched, Mh["h0"], Mh["relief_3km"])
        sc = np.array([b["final"] for b in (best_score(reg, a, c) for a, c in pts) if b])
        row[tag] = dict(n=len(sc), pct=float((sc < Sh["final"]).mean()*100),
                        mean=float(sc.mean()), p90=float(np.percentile(sc, 90)))
    rep.append(row)
    print(f"{name:16s} 史载θ={th:5.0f}° final={Sh['final']:.3f} | 自动θ={Ma['theta_back']:5.0f}° "
          f"final={Sa['final']:.3f} | naive={row['naive']['pct']:5.1f}% matched={row['matched']['pct']:5.1f}% "
          f"(n={row['matched']['n']}) faults={row['hist']['faults']}", flush=True)
    del reg
json.dump(rep, open('/home/user/fs/out/strict.json','w'), ensure_ascii=False, indent=1, default=float)
print("saved")
