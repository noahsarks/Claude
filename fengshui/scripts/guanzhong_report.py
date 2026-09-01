"""关中复核分析。与洛阳完全同协议；另报事先声明的去簇变体。"""
import json, math, base64, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy import ndimage, stats

SMOOTH_CELLS = 5          # 800 m x 5 = 4 km，与洛阳一致
QS = [95, 80, 55, 25]

G = np.load('out/guanzhong_grid.npy')
M = json.load(open('out/guanzhong_meta.json'))
lats = np.array(M['lats']); lons = np.array(M['lons']); B = M['box']
A = ndimage.uniform_filter(np.nan_to_num(G, nan=np.nanmean(G)), size=SMOOTH_CELLS)
TH = [np.percentile(A, q) for q in QS]
Gr = np.zeros_like(A, int)
for i, t in enumerate(TH):
    Gr[(Gr == 0) & (A >= t)] = i + 1
Gr[Gr == 0] = 5
AREA = [float((Gr == i).sum()) / Gr.size * 100 for i in range(1, 6)]

S = [s for s in json.load(open('guobao.json'))
     if B[0] < s['lat'] < B[1] and B[2] < s['lon'] < B[3]]
rows = []
for s in S:
    i = int(np.argmin(np.abs(lats - s['lat']))); j = int(np.argmin(np.abs(lons - s['lon'])))
    rows.append(dict(name=s['name'], lat=s['lat'], lon=s['lon'],
                     grade=int(Gr[i, j]), score=float(A[i, j]),
                     x=round((s['lon'] - lons[0]) / (lons[-1] - lons[0]) * 100, 2),
                     y=round((lats[0] - s['lat']) / (lats[0] - lats[-1]) * 100, 2)))

# 事先声明的去簇：2 km 内合并，保留该簇分数最高者
def declust(rs, km=2.0):
    out = []
    for r in sorted(rs, key=lambda x: -x['score']):
        if all(math.hypot((r['lat'] - o['lat']) * 110.54,
                          (r['lon'] - o['lon']) * 110.54 * math.cos(math.radians(r['lat']))) > km
               for o in out):
            out.append(r)
    return out

def report(rs, label):
    n = len(rs); k = len([r for r in rs if r['grade'] <= 2])
    hi = 100 * k / n
    gain = 1 - 20.0 / hi if hi > 0 else float('-inf')
    p = stats.binomtest(k, n, 0.20, alternative='greater').pvalue
    print(f"{label:22s} n={n:3d}  I+II 命中 {k:2d} = {hi:5.1f}%   增益 {gain:+.3f}   p = {p:.4f}")
    return dict(label=label, n=n, k=k, hi=hi, gain=gain, p=float(p))

print(f"关中：格点 {Gr.size}，尺度 3x，平滑 {SMOOTH_CELLS*0.8:.0f} km，各级面积 {[round(a,1) for a in AREA]}")
print(f"（洛阳同协议：n=24  I+II 命中 11 = 45.8%   增益 +0.564   p = 0.0038）\n")
r_all = report(rows, "全部点（主口径）")
dc = declust(rows)
r_dc = report(dc, "去簇 2 km（预声明）")

cm = ListedColormap(['#1c574c', '#40765d', '#6c7740', '#8e653a', '#7c4a36'])
fig = plt.figure(figsize=(lons.size / 26, lats.size / 26), dpi=200)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ax.imshow(Gr, cmap=cm, vmin=.5, vmax=5.5, interpolation='bilinear', aspect='auto')
fig.savefig('out/guanzhong_final.png', bbox_inches='tight', pad_inches=0)
b64 = base64.b64encode(open('out/guanzhong_final.png', 'rb').read()).decode()

rows.sort(key=lambda r: (r['grade'], -r['score']))
GN = ['I', 'II', 'III', 'IV', 'V']
print()
for r in rows:
    tag = '' if any(d['name'] == r['name'] for d in dc) else '  (簇内被合并)'
    print(f"   {GN[r['grade']-1]:>3s} {r['score']:.3f}  {r['name'][:20]}{tag}")
json.dump(dict(rows=rows, declustered=[d['name'] for d in dc], area=AREA,
               all=r_all, dc=r_dc, box=B, png=b64, smooth_km=SMOOTH_CELLS * 0.8, scale=3.0),
          open('out/guanzhong_report.json', 'w'), ensure_ascii=False, default=float)
