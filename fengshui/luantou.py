"""峦头评分引擎 v0.1 — 规则见 rules_luantou.yaml，每项指标对应一条原典条目。"""
import glob, math, re, numpy as np, rasterio
from scipy import ndimage
from skimage.morphology import reconstruction

DEM_DIR = "/home/user/fs/dem"
RES = 1.0 / 3600.0          # 1 arcsec
M_PER_DEG_LAT = 110540.0

# ── 瓦片与镶嵌 ────────────────────────────────────────────────
_TILES = {}
for _p in glob.glob(f"{DEM_DIR}/*.tif"):
    m = re.search(r"_(N|S)(\d+)_00_(E|W)(\d+)_00_", _p)
    _TILES[(int(m.group(2)), int(m.group(4)))] = _p

class Region:
    """以目标点为中心的 DEM 镶嵌 + 汇流网络。"""
    def __init__(self, name, lat, lon, pad=0.33, coarse=4):
        self.name, self.clat, self.clon = name, lat, lon
        la0, la1 = math.floor(lat - pad), math.floor(lat + pad)
        lo0, lo1 = math.floor(lon - pad), math.floor(lon + pad)
        rows = list(range(la1, la0 - 1, -1))           # 北→南
        cols = list(range(lo0, lo1 + 1))               # 西→东
        blocks = []
        for r in rows:
            row = []
            for c in cols:
                p = _TILES.get((r, c))
                if p is None:
                    row.append(np.full((3600, 3600), np.nan, np.float32))
                else:
                    with rasterio.open(p) as s:
                        row.append(s.read(1).astype(np.float32))
                    if not hasattr(self, "_ref"):
                        with rasterio.open(p) as s:
                            self._ref = (s.bounds.left, s.bounds.top, r, c)
            blocks.append(np.hstack(row))
        self.arr = np.vstack(blocks)
        left, top, rr, cc = self._ref
        self.west = left - (cc - cols[0])              # 镶嵌左上角经度
        self.north = top + (rows[0] - rr)              # 镶嵌左上角纬度
        self.arr[self.arr < -400] = np.nan
        self._filled = np.nan_to_num(self.arr, nan=0.0)   # 供 map_coordinates 复用，避免每次拷贝整幅
        self.mx = M_PER_DEG_LAT * math.cos(math.radians(lat))   # 每度经度米数
        self._drainage(coarse)

    # 像素 ↔ 经纬
    def rc(self, lat, lon):
        return (self.north - lat) / RES, (lon - self.west) / RES

    def sample(self, lats, lons):
        r, c = self.rc(np.asarray(lats), np.asarray(lons))
        return ndimage.map_coordinates(self._filled, [r, c], order=1, mode="nearest")

    # ── 汇流网络（填洼 → D8 → 累积）────────────────────────────
    def _drainage(self, f):
        a = self.arr
        H, W = (a.shape[0] // f) * f, (a.shape[1] // f) * f
        g = np.nanmean(a[:H, :W].reshape(H // f, f, W // f, f), axis=(1, 3)).astype(np.float32)
        g = np.nan_to_num(g, nan=np.nanmax(g))
        self.cg, self.cf = g, f
        self.cdy = RES * f * M_PER_DEG_LAT
        self.cdx = RES * f * self.mx
        # 填洼：形态学重建（erosion）
        seed = np.full_like(g, g.max()); seed[0, :] = g[0, :]; seed[-1, :] = g[-1, :]
        seed[:, 0] = g[:, 0]; seed[:, -1] = g[:, -1]
        fill = reconstruction(seed, g, method="erosion").astype(np.float32)
        self.fill = fill
        h, w = fill.shape
        offs = [(-1,0,self.cdy),(1,0,self.cdy),(0,-1,self.cdx),(0,1,self.cdx),
                (-1,-1,math.hypot(self.cdx,self.cdy)),(-1,1,math.hypot(self.cdx,self.cdy)),
                (1,-1,math.hypot(self.cdx,self.cdy)),(1,1,math.hypot(self.cdx,self.cdy))]
        best = np.zeros((h, w), np.float32); di = np.zeros((h, w), np.int8) - 1
        pad = np.pad(fill, 1, constant_values=np.inf)
        for k, (dr, dc, dist) in enumerate(offs):
            nb = pad[1+dr:1+dr+h, 1+dc:1+dc+w]
            drop = (fill - nb) / dist
            upd = drop > best
            best[upd] = drop[upd]; di[upd] = k
        self.d8, self.offs = di, offs
        # 累积：按高程降序单遍推流
        order = np.argsort(fill.ravel())[::-1]
        acc = np.ones(h * w, np.float32)
        dr_ = np.array([o[0] for o in offs]); dc_ = np.array([o[1] for o in offs])
        dif = di.ravel()
        for idx in order:
            k = dif[idx]
            if k < 0: continue
            r, c = divmod(int(idx), w)
            nr, nc = r + dr_[k], c + dc_[k]
            if 0 <= nr < h and 0 <= nc < w:
                acc[nr * w + nc] += acc[idx]
        self.acc = acc.reshape(h, w)
        cell_km2 = (self.cdx * self.cdy) / 1e6
        self.stream = self.acc * cell_km2 > 2.0          # 汇水 >2 km² 视为水道
        self.stream_rc = np.argwhere(self.stream)

    def crc(self, lat, lon):
        return (self.north - lat) / (RES * self.cf), (lon - self.west) / (RES * self.cf)

# ── 隶属函数 ──────────────────────────────────────────────────
def pl(x, pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return float(np.interp(x, xs, ys))

def bearing_diff(b, ref):
    return (b - ref + 180) % 360 - 180

# ── 单点指标 ──────────────────────────────────────────────────
def metrics(reg, lat, lon, R=6000.0, theta_deg=None):
    npix_lat = int(R / (RES * M_PER_DEG_LAT)) + 2
    npix_lon = int(R / (RES * reg.mx)) + 2
    r0, c0 = reg.rc(lat, lon)
    r0i, c0i = int(round(r0)), int(round(c0))
    rs = slice(max(0, r0i - npix_lat), min(reg.arr.shape[0], r0i + npix_lat + 1))
    cs = slice(max(0, c0i - npix_lon), min(reg.arr.shape[1], c0i + npix_lon + 1))
    win = reg.arr[rs, cs]
    if win.size < 100 or np.isnan(win).mean() > 0.3: return None
    rr = (np.arange(rs.start, rs.stop) - r0)[:, None]
    cc = (np.arange(cs.start, cs.stop) - c0)[None, :]
    dN = -rr * RES * M_PER_DEG_LAT
    dE = cc * RES * reg.mx
    dist = np.hypot(dN, dE)
    brg = (np.degrees(np.arctan2(dE, dN))) % 360
    h = np.nan_to_num(win, nan=np.nanmean(win))
    h0 = float(reg.sample([lat], [lon])[0])
    M = {}
    M["h0"] = h0
    r3 = (dist > 100) & (dist <= 3000)
    M["relief_3km"] = float(np.nanmax(h[r3]) - np.nanmin(h[r3])) if r3.any() else 0.0
    r6 = (dist > 100) & (dist <= R)
    M["relief_6km"] = float(np.nanmax(h[r6]) - np.nanmin(h[r6])) if r6.any() else 0.0

    # 坐山方向：0.3–2.5km 内高出穴部分的质量方向
    # 《葬经翼》「开面降势方名元武垂头」：来脉 = 上升最连贯、中途无凹断的方位
    rr_ = np.arange(0, 2401, 30.0)
    ths = np.arange(0, 360, 10.0)
    LA = lat + np.cos(np.radians(ths))[:, None] * rr_[None, :] / M_PER_DEG_LAT
    LO = lon + np.sin(np.radians(ths))[:, None] * rr_[None, :] / reg.mx
    P = reg.sample(LA.ravel(), LO.ravel()).reshape(len(ths), len(rr_))
    runm = np.maximum.accumulate(P, axis=1)
    broken = (runm - P) > 20.0                       # 凹断 >20 m 即视为脉断
    firstbrk = np.where(broken.any(1), broken.argmax(1), len(rr_))
    gain = np.array([runm[i, max(firstbrk[i] - 1, 0)] - h0 for i in range(len(ths))])
    if gain.max() < 30.0:                            # 平洋无脉可寻，退回高程质心
        band = (dist >= 300) & (dist <= 4000)
        wgt = np.clip(h - h0, 0, None) * band
        if wgt.sum() < 1e-6:
            theta = 0.0
        else:
            vN = float((wgt * dN / np.maximum(dist, 1)).sum()); vE = float((wgt * dE / np.maximum(dist, 1)).sum())
            theta = math.degrees(math.atan2(vE, vN)) % 360
    else:
        theta = float(ths[int(np.argmax(gain))])
    M["lai_gain"] = float(gain.max())
    if theta_deg is not None: theta = float(theta_deg)
    M["theta_back"] = theta

    d = bearing_diff(brg, theta)
    back  = (np.abs(d) <= 60)
    front = (np.abs(bearing_diff(brg, (theta + 180) % 360)) <= 45)
    left  = (np.abs(bearing_diff(brg, (theta + 90) % 360)) <= 37.5)
    right = (np.abs(bearing_diff(brg, (theta - 90) % 360)) <= 37.5)

    def sec(mask, lo, hi, q=75):
        m = mask & (dist >= lo) & (dist <= hi)
        return float(np.percentile(h[m], q)) - h0 if m.sum() > 20 else 0.0
    def ang(mask, lo, hi):
        m = mask & (dist >= lo) & (dist <= hi)
        if m.sum() < 20: return 0.0
        return float(np.degrees(np.arctan2(np.clip(h[m] - h0, 0, None), dist[m])).max())

    # R1 玄武垂头
    M["backing"] = sec(back, 300, 4000)
    prof_r = np.arange(0, 2001, 30.0)
    plat = lat + np.cos(math.radians(theta)) * prof_r / M_PER_DEG_LAT
    plon = lon + np.sin(math.radians(theta)) * prof_r / reg.mx
    prof = reg.sample(plat, plon)
    M["back_slope_near"] = float(np.degrees(np.arctan((prof[10] - prof[0]) / 300.0)))
    top = int(np.argmax(prof))                          # 靠山主峰在剖面上的位置
    seg = prof[:top + 1] if top >= 3 else prof[:4]
    run = np.maximum.accumulate(seg)
    M["back_dip"] = float(np.max(run - seg))            # 只量穴到主峰之间的凹断
    M["back_mono"] = float((np.diff(seg) >= -1.0).mean())
    M["back_top_m"] = float(top * 30.0)
    M["back_rise_300"] = float(prof[10] - prof[0])

    # R2 龙虎
    M["L_rise"], M["R_rise"] = sec(left, 200, 2000), sec(right, 200, 2000)
    M["L_ang"], M["R_ang"] = ang(left, 200, 2000), ang(right, 200, 2000)
    # 折臂：左右各 8 个方位的仰角序列是否有深缺口
    gaps = []
    for base in ((theta + 90) % 360, (theta - 90) % 360):
        seq = []
        for k in range(-3, 4):
            b = (base + k * 12) % 360
            m = (np.abs(bearing_diff(brg, b)) <= 6) & (dist >= 200) & (dist <= 2000)
            seq.append(np.degrees(np.arctan2(np.clip(h[m]-h0,0,None), dist[m])).max() if m.sum() > 5 else 0.0)
        seq = np.array(seq); med = np.median(seq)
        gaps.append(float((seq < med * 0.5).sum() / len(seq)) if med > 0.5 else 0.0)
    M["gap_ratio"] = max(gaps)

    # R3 向背
    gy, gx = np.gradient(h, RES * M_PER_DEG_LAT, RES * reg.mx)
    aN, aE = gy, -gx                      # 坡面下降方向（朝向低处）
    toN, toE = -dN / np.maximum(dist, 1), -dE / np.maximum(dist, 1)   # 指向穴
    dot = (aN * toN + aE * toE) / np.maximum(np.hypot(aN, aE), 1e-6)
    ring2 = (dist >= 300) & (dist <= 3000)
    M["facing_ratio"] = float((dot[ring2] > 0).mean()) if ring2.sum() > 50 else 0.5

    # R4 明堂
    mf = front & (dist >= 100) & (dist <= 800)
    if mf.sum() > 20:
        gmag = np.degrees(np.arctan(np.hypot(gy, gx)))
        M["front_slope"] = float(np.mean(gmag[mf]))
        M["front_drop"] = h0 - float(np.median(h[mf]))
    else:
        M["front_slope"], M["front_drop"] = 20.0, -50.0
    M["front_open"] = ang(front, 200, 1200)
    M["an_ang"] = ang(front, 300, 2000)
    M["chao_ang"] = ang(front, 2000, 6000)

    # R8 藏风
    near = dist <= 500
    M["tpi"] = h0 - float(np.mean(h[near]))
    bar = []
    for k in range(36):
        b = k * 10.0
        m = (np.abs(bearing_diff(brg, b)) <= 5) & (dist >= 100) & (dist <= 3000)
        bar.append(np.degrees(np.arctan2(np.clip(h[m]-h0,0,None), dist[m])).max() if m.sum() > 5 else 0.0)
    M["barrier"] = float((np.array(bar) > 2.0).mean())

    # F6 破面：坡面粗糙度
    M["tri"] = float(np.std(h[(dist <= 300)]))

    # R6/R7 水
    M.update(_water(reg, lat, lon, h0, theta))
    return M

def _water(reg, lat, lon, h0, theta):
    out = {"d_water": 9999.0, "bank": 0.0, "sinuosity": 1.0, "lock": 1.0}
    if reg.stream_rc.size == 0: return out
    cr, cc = reg.crc(lat, lon)
    d = np.hypot((reg.stream_rc[:, 0] - cr) * reg.cdy, (reg.stream_rc[:, 1] - cc) * reg.cdx)
    i = int(np.argmin(d)); out["d_water"] = float(d[i])
    if d[i] > 6000: return out
    pr, pc = reg.stream_rc[i]
    # 沿河道上下游各走 ~1.2km，取通道点列
    pts = [(pr, pc)]
    r, c = pr, pc
    for _ in range(12):                       # 下游
        k = reg.d8[r, c]
        if k < 0: break
        r, c = r + reg.offs[k][0], c + reg.offs[k][1]
        if not (0 <= r < reg.d8.shape[0] and 0 <= c < reg.d8.shape[1]): break
        pts.append((r, c))
    down = list(pts)
    up = []                                    # 上游：邻域内汇流最大的上游格
    r, c = pr, pc
    for _ in range(12):
        best, bp = -1, None
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0: continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < reg.d8.shape[0] and 0 <= nc < reg.d8.shape[1]): continue
                k = reg.d8[nr, nc]
                if k < 0: continue
                if (nr + reg.offs[k][0], nc + reg.offs[k][1]) == (r, c) and reg.acc[nr, nc] > best:
                    best, bp = reg.acc[nr, nc], (nr, nc)
        if bp is None: break
        up.append(bp); r, c = bp
    chan = list(reversed(up)) + down
    if len(chan) >= 5:
        P = np.array([[(q[1] - cc) * reg.cdx, -(q[0] - cr) * reg.cdy] for q in chan])  # 以穴为原点(E,N)
        seg = np.hypot(*np.diff(P, axis=0).T).sum()
        chord = float(np.hypot(*(P[-1] - P[0])))
        out["sinuosity"] = float(seg / chord) if chord > 1 else 1.0
        # 圆拟合定凹凸岸
        A = np.c_[2 * P, np.ones(len(P))]
        b = (P ** 2).sum(1)
        try:
            sol, *_ = np.linalg.lstsq(A, b, rcond=None)
            O = sol[:2]; Rad = math.sqrt(max(sol[2] + (O ** 2).sum(), 1e-6))
            if Rad < 5000 and out["d_water"] < 800:
                out["bank"] = 1.0 if np.hypot(*O) < Rad else -1.0    # 穴在圆心侧=凹岸=环抱
        except Exception:
            pass
    # 水口关锁：谷宽 = 河道两侧升高 30m 之前的横向距离
    def vwidth(r, c):
        hc = reg.fill[r, c]; tot = 0.0
        k = reg.d8[r, c]
        fr, fc = (reg.offs[k][0], reg.offs[k][1]) if k >= 0 else (0, 1)
        pr, pc = -fc, fr                      # 垂直于流向
        n = max(abs(pr), abs(pc)) or 1
        pr, pc = int(round(pr / n)), int(round(pc / n))
        for dr, dc in ((pr, pc), (-pr, -pc)):
            for s in range(1, 25):
                nr, nc = r + dr * s, c + dc * s
                if not (0 <= nr < reg.fill.shape[0] and 0 <= nc < reg.fill.shape[1]): break
                if reg.fill[nr, nc] - hc > 30: break
                tot += math.hypot(dr * reg.cdy, dc * reg.cdx)
        return max(tot, reg.cdx)
    if len(down) >= 6:
        w_t = vwidth(*down[0]); w_g = min(vwidth(*q) for q in down[2:])
        out["lock"] = float(w_t / max(w_g, 1.0))
    return out

# ── 评分 ──────────────────────────────────────────────────────
W_MOUNT = dict(water=.22, water_gate=.10, mingtang=.18, xuanwu=.16, hulong=.12, xiangbei=.12, zangfeng=.10)
W_PLAIN = dict(water=.34, water_gate=.14, mingtang=.22, xuanwu=.08, hulong=.06, xiangbei=.13, zangfeng=.03)

def score(M):
    if M is None: return None
    c = {}
    c["xuanwu"] = .45*pl(M["backing"], [(-50,0),(0,.12),(50,1),(300,1),(800,.55),(1500,.3)]) \
                + .30*pl(M["back_slope_near"], [(0,.2),(3,.8),(8,1),(20,1),(30,.5),(45,.1)]) \
                + .25*pl(M["back_mono"], [(.5,0),(.75,.5),(.92,1)])
    c["hulong"] = .40*pl(min(M["L_rise"], M["R_rise"]), [(-30,0),(0,.25),(30,.8),(120,1),(500,1)]) \
                + .35*(1 - abs(M["L_rise"]-M["R_rise"]) / max(abs(M["L_rise"]), abs(M["R_rise"]), 1.0)) \
                + .25*pl(max(M["L_ang"], M["R_ang"]), [(0,.4),(5,1),(18,1),(30,.3),(45,0)])
    c["xiangbei"] = pl(M["facing_ratio"], [(.30,0),(.50,.40),(.65,.85),(.80,1)])
    c["mingtang"] = .25*pl(M["front_slope"], [(0,1),(6,1),(15,.4),(30,0)]) \
                  + .20*pl(M["front_drop"], [(-50,0),(0,.5),(10,1),(150,1)]) \
                  + .25*pl(M["front_open"], [(0,.45),(1,.8),(3,1),(8,.7),(15,.25),(25,0)]) \
                  + .30*(.6*pl(M["an_ang"], [(0,0),(1.5,.5),(3,1),(8,1),(15,.4),(25,0)])
                       + .4*pl(M["chao_ang"], [(0,.2),(1,.7),(3,1),(10,.8),(20,.5)]))
    bank = {1.0:1.0, -1.0:.15, 0.0:.6}[M["bank"]]
    c["water"] = .45*pl(M["d_water"], [(0,.10),(50,.35),(120,1),(800,1),(2000,.45),(4000,.15),(8000,0)]) \
               + .30*bank + .25*pl(M["sinuosity"], [(1.0,.2),(1.1,.5),(1.3,1),(3,1)])
    c["water_gate"] = pl(M["lock"], [(0.5,.1),(1,.2),(1.5,.5),(2.5,.85),(4,1),(20,1)])
    c["zangfeng"] = .5*pl(M["tpi"], [(-120,1),(-20,1),(0,.7),(20,.4),(60,.15),(150,0)]) \
                  + .5*pl(M["barrier"], [(0,0),(.3,.4),(.6,.85),(.85,1)])
    mode = "plain" if M["relief_3km"] < 120 else "mountain"
    W = W_PLAIN if mode == "plain" else W_MOUNT
    base = sum(W[k] * min(max(c[k], 0), 1) for k in W)
    F = {}
    if M["back_dip"] > 40:                      F["F1_拒尸"] = .25
    if M["back_rise_300"] > 150:                F["F2_坠足"] = .20
    if M["gap_ratio"] >= 0.30:                  F["F3_折臂"] = .15
    if M["d_water"] < 50:                       F["F4_割脚"] = .20
    if M["bank"] < 0 and M["d_water"] < 800 and M["sinuosity"] > 1.15: F["F5_反跳"] = .20
    if max(M["L_ang"], M["R_ang"]) > 30:        F["F7_高压"] = .15
    disc = 1.0
    for v in F.values(): disc *= (1 - v)
    return dict(components=c, mode=mode, base=base, faults=F, final=base * disc)
