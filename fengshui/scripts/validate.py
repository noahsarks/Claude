import sys, math, json, numpy as np
sys.path.insert(0, '/home/user/fs')
import luantou as L

TARGETS = [
    ("明十三陵·长陵",   40.2967, 116.2331, "帝陵/山地"),
    ("北京故宫·太和殿", 39.9151, 116.3972, "宫殿/平原"),
    ("唐乾陵·梁山",     34.5806, 108.2144, "帝陵/山地"),
    ("秦始皇陵·封土",   34.3814, 109.2533, "帝陵/平原"),
    ("清东陵·孝陵",     40.1997, 117.6417, "帝陵/山地"),
]
RNG = np.random.default_rng(20260831)
N_MATCH, N_NAIVE = 180, 180

def quick(reg, lat, lon):
    """便宜筛选：高程 + 3km 起伏度"""
    r0, c0 = reg.rc(lat, lon)
    kr = int(3000 / (L.RES * L.M_PER_DEG_LAT)); kc = int(3000 / (L.RES * reg.mx))
    r0, c0 = int(r0), int(c0)
    if r0 - kr < 0 or c0 - kc < 0 or r0 + kr >= reg.arr.shape[0] or c0 + kc >= reg.arr.shape[1]:
        return None
    w = reg.arr[r0-kr:r0+kr, c0-kc:c0+kc]
    if np.isnan(w).mean() > 0.2: return None
    return float(reg.arr[r0, c0]), float(np.nanmax(w) - np.nanmin(w))

def sample_pts(reg, lat, lon, n, matched, h0, rel0):
    out, tries = [], 0
    margin = 6200
    while len(out) < n and tries < n * 60:
        tries += 1
        d = math.sqrt(RNG.uniform(5000**2, 25000**2))
        b = RNG.uniform(0, 360)
        la = lat + math.cos(math.radians(b)) * d / L.M_PER_DEG_LAT
        lo = lon + math.sin(math.radians(b)) * d / reg.mx
        # 需留出 6km 分析窗
        rr, cc = reg.rc(la, lo)
        if not (margin/(L.RES*L.M_PER_DEG_LAT) < rr < reg.arr.shape[0]-margin/(L.RES*L.M_PER_DEG_LAT)): continue
        if not (margin/(L.RES*reg.mx) < cc < reg.arr.shape[1]-margin/(L.RES*reg.mx)): continue
        q = quick(reg, la, lo)
        if q is None: continue
        if matched:
            if abs(q[0] - h0) > 150: continue
            if not (0.6 * rel0 <= q[1] <= 1.7 * rel0): continue
        out.append((la, lo))
    return out

report = []
for name, lat, lon, kind in TARGETS:
    reg = L.Region(name, lat, lon, pad=0.33)
    Mt = L.metrics(reg, lat, lon); St = L.score(Mt)
    h0, rel0 = Mt["h0"], Mt["relief_3km"]
    res = {"name": name, "kind": kind, "target": St, "metrics": Mt}
    for tag, matched, n in (("naive", False, N_NAIVE), ("matched", True, N_MATCH)):
        pts = sample_pts(reg, lat, lon, n, matched, h0, rel0)
        sc, comps = [], []
        for la, lo in pts:
            s = L.score(L.metrics(reg, la, lo))
            if s: sc.append(s["final"]); comps.append(s["components"])
        sc = np.array(sc)
        res[tag] = {
            "n": len(sc),
            "pct": float((sc < St["final"]).mean() * 100) if len(sc) else float("nan"),
            "mean": float(sc.mean()) if len(sc) else float("nan"),
            "std": float(sc.std()) if len(sc) else float("nan"),
            "p90": float(np.percentile(sc, 90)) if len(sc) else float("nan"),
            "comp_mean": {k: float(np.mean([c[k] for c in comps])) for k in comps[0]} if comps else {},
        }
    report.append(res)
    print(f"[{name}] target={St['final']:.3f} naive_pct={res['naive']['pct']:.1f} matched_pct={res['matched']['pct']:.1f}", flush=True)
    del reg

json.dump(report, open('/home/user/fs/out/validation.json','w'), ensure_ascii=False, indent=1, default=float)
print("saved")
