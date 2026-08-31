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
        # 河流等级用汇水面积代替 Strahler（单调等价，且无需遍历河网拓扑）
        # 无定河实证：6~7 级干流遗址密度 842.9，3~5 级 252.3，1~2 级 85.2 处/10^4km
        self.acc_km2 = self.acc * cell_km2

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
    # 贴身龙虎(形) 与 外龙虎/水口砂(势)：明十三陵龙山虎山在陵前 6 km，贴身砂仅数百米
    M["L_rise"], M["R_rise"] = sec(left, 200, 1200), sec(right, 200, 1200)
    M["L_ang"],  M["R_ang"]  = ang(left, 200, 1200), ang(right, 200, 1200)
    M["Lout"],   M["Rout"]   = sec(left, 2000, 6000), sec(right, 2000, 6000)
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
    of = front & (dist >= 2000) & (dist <= 6000)      # 案外大堂：规模宏阔
    M["outer_open"] = float(np.mean(np.degrees(np.arctan2(np.clip(h[of]-h0,0,None), dist[of])))) if of.sum() > 20 else 0.0

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
    # 地貌类型 —— 无定河实证中排第一位的因子（黄土丘陵密度 182.6 vs 山地 25.3
    # vs 洪积平原 18.9 处/10^4km²）。此处按 3km 起伏度 + 局部坡度 + 粗糙度粗分四类。
    loc = dist <= 1000
    slope_loc = float(np.mean(np.degrees(np.arctan(np.hypot(*np.gradient(
        h, RES*M_PER_DEG_LAT, RES*reg.mx))))[loc])) if loc.sum() > 20 else 0.0
    M["slope_local"] = slope_loc
    r3 = M["relief_3km"]
    if r3 >= 400 and slope_loc >= 12:        M["landform"] = "山地"
    elif r3 < 120 and slope_loc < 6:         M["landform"] = "平原"
    elif r3 >= 150 and M["tri"] > 0.055 * r3: M["landform"] = "破碎沟壑"
    else:                                    M["landform"] = "丘陵台塬"

    # 《葬经》五不葬 —— 过山：「气以势止」。原文注给的操作判据是
    # 「没有诸水会聚、群砂聚集」，故按此二者判定，而非自拟坡度比。
    sg = []
    for k in range(24):
        b = k * 15.0
        m2 = (dist >= 300) & (dist <= 1500) & (np.abs(bearing_diff(brg, b)) <= 7.5)
        sg.append(1 if (m2.sum() > 5 and np.percentile(h[m2], 75) - h0 > 15) else 0)
    M["sand_gather"] = float(np.mean(sg))            # 群砂聚集
    # 独山：「气以龙会」，无过脉与外相连者不可葬
    # 判据：1.5–3 km 环带上，高于穴 30 m 的方位占比（有脉相连则不止一个方向高）
    rr2 = (dist >= 1500) & (dist <= 3000)
    conn = []
    for k in range(24):
        b = k * 15.0
        m2 = rr2 & (np.abs(bearing_diff(brg, b)) <= 7.5)
        conn.append(1 if (m2.sum() > 5 and np.percentile(h[m2], 75) - h0 > 30) else 0)
    M["ridge_conn"] = float(np.mean(conn))          # 独山 → 接近 0
    # 真龙「两水相夹送」：来龙方位两侧各 60° 内是否都有水道
    M["flank_water"] = 0.0

    # R6/R7 水
    M.update(_water(reg, lat, lon, h0, theta))
    M["flank_water"] = _flank_water(reg, lat, lon, theta)
    M["water_converge"] = _converge(reg, lat, lon)
    return M

def _converge(reg, lat, lon, R=2000.0):
    """诸水会聚：R 内汇流点（两条上游支流交汇）的个数。"""
    if reg.stream_rc.size == 0: return 0.0
    cr, cc = reg.crc(lat, lon)
    d = np.hypot((reg.stream_rc[:,0]-cr)*reg.cdy, (reg.stream_rc[:,1]-cc)*reg.cdx)
    n = 0
    for (r, c) in reg.stream_rc[d < R]:
        ups = 0
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr == dc == 0: continue
                nr, nc = r+dr, c+dc
                if not (0 <= nr < reg.d8.shape[0] and 0 <= nc < reg.d8.shape[1]): continue
                k = reg.d8[nr, nc]
                if k < 0: continue
                if (nr+reg.offs[k][0], nc+reg.offs[k][1]) == (r, c) and reg.acc[nr, nc]*(reg.cdx*reg.cdy/1e6) > 0.5: ups += 1
        if ups >= 2: n += 1
    return float(n)


def _flank_water(reg, lat, lon, theta):
    """《寻龙》真龙气脉必有两水相夹送：来龙轴线左右两侧 3 km 内是否各有水道。"""
    if reg.stream_rc.size == 0: return 0.0
    cr, cc = reg.crc(lat, lon)
    dy = (reg.stream_rc[:, 0] - cr) * reg.cdy * -1.0
    dx = (reg.stream_rc[:, 1] - cc) * reg.cdx
    d = np.hypot(dx, dy)
    sel = d < 3000
    if sel.sum() == 0: return 0.0
    b = (np.degrees(np.arctan2(dx[sel], dy[sel]))) % 360
    rel = (b - theta + 180) % 360 - 180
    left  = ((rel > 20) & (rel < 160)).any()
    right = ((rel < -20) & (rel > -160)).any()
    return float(left) * 0.5 + float(right) * 0.5


def _water(reg, lat, lon, h0, theta):
    out = {"d_water": 9999.0, "bank": 0.0, "sinuosity": 1.0, "lock": 1.0,
           "dh_water": 999.0, "river_km2": 0.0}
    if reg.stream_rc.size == 0: return out
    cr, cc = reg.crc(lat, lon)
    d = np.hypot((reg.stream_rc[:, 0] - cr) * reg.cdy, (reg.stream_rc[:, 1] - cc) * reg.cdx)
    i = int(np.argmin(d)); out["d_water"] = float(d[i])
    pr0, pc0 = reg.stream_rc[i]
    # 《无定河》实证：距河流垂直距离 <40 m 者占 213/293，比水平距离更具区分度。
    # 这同时是"二级阶地"的可计算代理——洛阳盆地二里头/偃师商城/周王城/汉魏故城/
    # 隋唐洛阳城五座都邑均位于二级阶地上。
    out["dh_water"] = float(h0 - reg.fill[pr0, pc0])
    # 河流等级：取 1.5 km 内最大汇水面积代表本地水系级别
    dm = d < 1500
    if dm.any():
        out["river_km2"] = float(max(reg.acc_km2[r, c] for r, c in reg.stream_rc[dm]))
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
# 注：v0.3 未设独立"向阳"项。《无定河》实证显示坡向对聚落选址无显著倾向，
# 且作者用多角度光照模拟证明该流域阴坡实际同样受光充足，坡向与光照关联度很低。
W_MOUNT = dict(water=.24, water_gate=.09, mingtang=.18, xuanwu=.15, hulong=.11, xiangbei=.12, zangfeng=.11)
W_PLAIN = dict(water=.34, water_gate=.14, mingtang=.22, xuanwu=.08, hulong=.06, xiangbei=.13, zangfeng=.03)

def score(M):
    """《葬经》「千尺为势，百尺为形，势与形顺者吉，势与形逆者凶。
    势凶形吉，百福希一。势吉形凶，祸不旋日」——势与形是乘性关系，不是加权和。"""
    if M is None: return None
    c = {}
    c["xuanwu"] = .45*pl(M["backing"], [(-50,0),(0,.12),(50,1),(300,1),(800,.55),(1500,.3)]) \
                + .30*pl(M["back_slope_near"], [(0,.2),(3,.8),(8,1),(20,1),(30,.5),(45,.1)]) \
                + .25*pl(M["back_mono"], [(.5,0),(.75,.5),(.92,1)])
    # 龙虎双尺度：贴身砂(形) 七成，外龙虎/水口砂(势) 三成
    near_hu = .40*pl(min(M["L_rise"], M["R_rise"]), [(-30,0),(0,.25),(30,.8),(120,1),(500,1)]) \
            + .35*(1 - abs(M["L_rise"]-M["R_rise"]) / max(abs(M["L_rise"]), abs(M["R_rise"]), 1.0)) \
            + .25*pl(max(M["L_ang"], M["R_ang"]), [(0,.4),(5,1),(18,1),(30,.3),(45,0)])
    out_hu  = pl(min(M["Lout"], M["Rout"]), [(-100,0),(0,.3),(50,.7),(200,1),(900,1)])
    c["hulong"] = .70*near_hu + .30*out_hu
    c["xiangbei"] = pl(M["facing_ratio"], [(.30,0),(.50,.40),(.65,.85),(.80,1)])
    # 明堂两层：案内明堂 + 案外大堂（清东陵相度档案「案内明堂舒畅开阳，案外大堂规模宏阔」）
    inner = .30*pl(M["front_slope"], [(0,1),(6,1),(15,.4),(30,0)]) \
          + .25*pl(M["front_drop"], [(-50,0),(0,.5),(10,1),(150,1)]) \
          + .45*pl(M["front_open"], [(0,.45),(1,.8),(3,1),(8,.7),(15,.25),(25,0)])
    outer = .55*pl(M["outer_open"], [(0,.3),(1,.8),(3,1),(9,.6),(18,.2)]) \
          + .45*(.6*pl(M["an_ang"], [(0,0),(1.5,.5),(3,1),(8,1),(15,.4),(25,0)])
               + .4*pl(M["chao_ang"], [(0,.2),(1,.7),(3,1),(10,.8),(20,.5)]))
    c["mingtang"] = .60*inner + .40*outer
    bank = {1.0:1.0, -1.0:.15, 0.0:.6}[M["bank"]]
    # 水平距离隶属函数按《无定河》实证重标定：<300m 密度 376.7、300-600m 153.7、
    # >600m 21.9 —— 实证是"越近越好"，原 v0.2 的 120-800m 平顶偏离实证。
    c["water"] = .28*pl(M["d_water"], [(0,.55),(60,.85),(300,1),(600,.65),(1200,.35),(3000,.12),(8000,0)]) \
               + .20*bank + .14*pl(M["sinuosity"], [(1.0,.2),(1.1,.5),(1.3,1),(3,1)]) \
               + .12*M.get("flank_water", 0.0) \
               + .16*pl(M.get("dh_water",999), [(-5,.2),(3,.7),(15,1),(40,1),(90,.55),(180,.2),(400,0)]) \
               + .10*pl(M.get("river_km2",0), [(0,.1),(5,.35),(50,.7),(300,1),(5000,1)])
    c["water_gate"] = pl(M["lock"], [(0.5,.1),(1,.2),(1.5,.5),(2.5,.85),(4,1),(20,1)])
    c["zangfeng"] = .5*pl(M["tpi"], [(-120,1),(-20,1),(0,.7),(20,.4),(60,.15),(150,0)]) \
                  + .5*pl(M["barrier"], [(0,0),(.3,.4),(.6,.85),(.85,1)])
    mode = "plain" if M["relief_3km"] < 120 else "mountain"
    W = W_PLAIN if mode == "plain" else W_MOUNT
    for k in W: c[k] = min(max(c[k], 0), 1)

    # ── 势 与 形 ──────────────────────────────────────────────
    # 势(千尺)：玄武、外龙虎/外堂、水口关锁；形(百尺)：内明堂、贴身龙虎、得水、向背
    shi  = (.45*c["xuanwu"] + .25*outer + .30*c["water_gate"])
    xing = (.35*inner + .30*near_hu + .20*c["water"] + .15*c["xiangbei"])
    base = sum(W[k]*c[k] for k in W)
    # 「势与形逆者凶」：失配惩罚，且不对称——「势凶形吉，百福希一」重于「势吉形凶」
    gap = shi - xing
    if gap < 0:   mism = 1 - min(1.0, (-gap) * 1.30)     # 势凶形吉：罚重
    else:         mism = 1 - min(1.0, gap * 0.75)        # 势吉形凶：罚轻
    mism = max(mism, 0.15)

    # ── 凶格 ──────────────────────────────────────────────────
    # 《葬经》四势「形势反此，法当破死」——否决级，故系数远重于一般扣分
    F = {}
    if M["back_dip"] > 40:                          F["拒尸(玄武不垂)"] = .40
    if M["bank"] < 0 and M["d_water"] < 800 and M["sinuosity"] > 1.15:
                                                    F["腾去(朱雀不舞)"] = .40
    if M["R_ang"] > 30:                             F["衔尸(虎蹲)"] = .35
    if M["L_ang"] > 30:                             F["嫉主(龙踞)"] = .35
    # 《葬经》五不葬「童断石过独，生新凶，消已福」
    if M["back_rise_300"] > 150:                    F["断山(坠足)"] = .25
    # 五不葬原文为「山之不可葬者五」，只适用于山陇；《葬经》另云「平原无山只看水」，
    # 故平洋模式下不判过山/独山——平原本无山可言。
    if mode == "mountain":
        if M.get("sand_gather",1) < .25 and M.get("water_converge",1) < 1:
                                                    F["过山(势未止)"] = .30
        if M.get("ridge_conn",1) < .15:             F["独山(气不会)"] = .35
    if M["gap_ratio"] >= 0.30:                      F["折臂"] = .15
    if M["d_water"] < 50:                           F["割脚"] = .20
    disc = 1.0
    for v in F.values(): disc *= (1 - v)
    return dict(components=c, mode=mode, base=base, shi=shi, xing=xing,
                mismatch=mism, faults=F, final=base*mism*disc)
