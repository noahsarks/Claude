import sys, math, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L
from validate import quick, sample_pts, RNG

CASES = [
    ("清东陵·孝陵(修正)",  40.1857, 117.6390, "维基 40°11′09″N 117°38′20″E"),
    ("乾陵·北峰玄宫",      34.5815, 108.2129, "DEM局部最高1045.7m≈文献1047.9m"),
    ("乾陵·北峰南麓600m",  34.5761, 108.2129, "献殿一带,山南坡"),
    ("乾陵·南二峰间神道",  34.5545, 108.2129, "双乳峰阙门之间"),
]
out=[]
for name, lat, lon, why in CASES:
    reg = L.Region(name, lat, lon, pad=0.33)
    M = L.metrics(reg, lat, lon); S = L.score(M)
    pts = sample_pts(reg, lat, lon, 180, True, M["h0"], M["relief_3km"])
    sc = np.array([s["final"] for s in (L.score(L.metrics(reg,a,b)) for a,b in pts) if s])
    pct = float((sc < S["final"]).mean()*100)
    out.append(dict(name=name, why=why, final=S["final"], mode=S["mode"], pct=pct,
                    n=len(sc), faults=list(S["faults"]), comp=S["components"], m=M))
    print(f"{name:22s} h0={M['h0']:6.0f} 坐山={M['theta_back']:3.0f}° backing={M['backing']:6.0f} tpi={M['tpi']:6.0f} "
          f"final={S['final']:.3f} matched_pct={pct:5.1f}%  faults={list(S['faults'])}", flush=True)
    del reg
json.dump(out, open('/home/user/fs/out/revalidation.json','w'), ensure_ascii=False, indent=1, default=float)
