"""3x 分级图的 Kvamme 分析 + 纯栅格 PNG（不含任何文字，标注交给 HTML 层）。"""
import json, base64, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy import stats

G = np.load('out/luoyang3x_grid.npy')
M = json.load(open('out/luoyang3x_meta.json'))
lats = np.array(M['lats']); lons = np.array(M['lons'])
ok = np.isfinite(G)

QS = [95, 80, 55, 25]
TH = [np.nanpercentile(G, q) for q in QS]
Gr = np.zeros_like(G, dtype=int)
for i, t in enumerate(TH):
    Gr[np.isfinite(G) & (Gr == 0) & (G >= t)] = i + 1
Gr[np.isfinite(G) & (Gr == 0)] = 5
AREA = [float((Gr == i).sum()) / ok.sum() * 100 for i in range(1, 6)]

B = M['box']
SITES = [s for s in json.load(open('guobao.json'))
         if B[0] < s['lat'] < B[1] and B[2] < s['lon'] < B[3]]
SITES += [{"name": "汉魏洛阳故城*", "lat": 34.7256, "lon": 112.5747},
          {"name": "偃师商城*", "lat": 34.7167, "lon": 112.7833}]

def at(la, lo):
    i = int(np.argmin(np.abs(lats - la))); j = int(np.argmin(np.abs(lons - lo)))
    return int(Gr[i, j]), float(G[i, j])

rows = []
for s in SITES:
    g, v = at(s['lat'], s['lon'])
    rows.append(dict(name=s['name'], lat=s['lat'], lon=s['lon'], grade=g, score=v,
                     x=float((s['lon'] - lons[0]) / (lons[-1] - lons[0]) * 100),
                     y=float((lats[0] - s['lat']) / (lats[0] - lats[-1]) * 100)))
rows.sort(key=lambda r: (r['grade'], -r['score']))
n = len(rows)

def kv(a, p): return 1 - a / p if p > 0 else float('-inf')
cum_a = AREA[0] + AREA[1]
k = len([r for r in rows if 0 < r['grade'] <= 2])
cum_s = 100 * k / n
p = stats.binomtest(k, n, cum_a / 100, alternative='greater').pvalue

print(f"格点 {ok.sum()}  古迹 {n} 处   尺度 {M['scale']:.0f}x")
print(f"{'级':>4s}{'占面积%':>9s}{'占古迹%':>9s}{'增益':>9s}")
NAMES = ['I', 'II', 'III', 'IV', 'V']
per = []
for i in range(5):
    ps = 100 * len([r for r in rows if r['grade'] == i + 1]) / n
    per.append(ps)
    print(f"{NAMES[i]:>4s}{AREA[i]:9.1f}{ps:9.1f}{kv(AREA[i], ps):9.3f}")
print(f"\nI+II: 面积 {cum_a:.1f}%  古迹 {cum_s:.1f}%  Kvamme 增益 = {kv(cum_a, cum_s):+.3f}   二项 p = {p:.4f}")
print(f"（1x 对照：I+II 古迹 12.5%，增益 -0.600，p = 0.886）\n")
for r in rows:
    print(f"{r['name'][:20]:22s}{NAMES[r['grade']-1]:>4s}{r['score']:8.3f}")

cmap = ListedColormap(['#1c574c', '#40765d', '#6c7740', '#8e653a', '#7c4a36'])
fig = plt.figure(figsize=(lons.size / 100 * 4, lats.size / 100 * 4), dpi=150)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ax.imshow(Gr, cmap=cmap, vmin=.5, vmax=5.5, interpolation='nearest', aspect='auto')
fig.savefig('out/luoyang3x_raster.png', bbox_inches='tight', pad_inches=0)
b64 = base64.b64encode(open('out/luoyang3x_raster.png', 'rb').read()).decode()
json.dump(dict(area=AREA, per_grade_sites=per, rows=rows, n=n,
               gain_I_II=kv(cum_a, cum_s), gain_I=kv(AREA[0], per[0]),
               binom_p=float(p), thresholds=[float(t) for t in TH],
               box=B, scale=M['scale'], png_b64=b64),
          open('out/luoyang3x_report.json', 'w'), ensure_ascii=False, default=float)
print(f"\n栅格 PNG {len(b64)//1024} KB (base64)")
