"""峦头评分引擎 v0.7 — 规则见 rules_luantou.yaml，每项指标对应一条原典条目。"""
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
        # ── 平地导流（v0.8 修）────────────────────────────────────
        # 形态学填洼会造出严格水平的平面，平面上 8 邻域落差全为 0，
        # 上面那段 `drop > best`（best 初值 0）便给不出方向，汇流在此中断。
        # 实测（单瓦片）：6.4% 的内部格无下游，其中 100% 是填洼造出的严格平地；
        # 3×3 瓦片区最大流域仅占区域面积 0.22%——洛河这类干流根本没被识别出来。
        # 平原正是平地最多的地方，所以这个缺陷恰好在最需要水系的地方最严重。
        #
        # 解法用 Garbrecht & Martz (1997) 的双梯度法：在平地上叠一个极小的合成坡降，
        #   ① 背离高地（离「与更高地相邻的平地格」越远越低）
        #   ② 趋向出口（离「与更低地相邻的平地格」越近越低），权重 2 倍
        # 然后在 fill+ε·梯度 上重排 D8。ε 取 1e-3 m/步，远小于 DEM 垂直分辨率。
        flat = np.zeros((h, w), bool)
        flat[1:-1, 1:-1] = (di < 0)[1:-1, 1:-1]
        if flat.any():
            fpad = np.pad(fill.astype(np.float64), 1, constant_values=np.inf)
            nb_hi = np.zeros((h, w), bool); nb_lo = np.zeros((h, w), bool)
            for dr, dc, _ in offs:
                nb = fpad[1+dr:1+dr+h, 1+dc:1+dc+w]
                nb_hi |= nb > fill                       # 邻有更高地
                nb_lo |= nb < fill                       # 邻有更低地（即出口）
            K3 = np.ones((3, 3), bool)
            def bfs_from(seed):
                dist = np.full((h, w), -1, np.int32)
                cur = seed & flat
                dist[cur] = 0
                k = 0
                while cur.any():
                    k += 1
                    cur = ndimage.binary_dilation(cur, K3) & flat & (dist < 0)
                    dist[cur] = k
                return dist, k
            dh, kh = bfs_from(nb_hi)                     # 距高地
            dl, kl = bfs_from(nb_lo)                     # 距出口
            dh[dh < 0] = kh + 1                          # 平地内与高地不连通者
            dl[dl < 0] = kl + 1
            grad = np.zeros((h, w), np.float64)
            grad[flat] = 2.0 * dl[flat] + (kh + 1 - dh[flat])
            synth = fill.astype(np.float64) + 1e-3 * grad
            # 只对平地格重排方向（非平地格已有真实落差，不动）
            spad = np.pad(synth, 1, constant_values=np.inf)
            bestdrop = np.zeros((h, w))
            for k, (dr, dc, dist_) in enumerate(offs):
                nb = spad[1+dr:1+dr+h, 1+dc:1+dc+w]
                drop = (synth - nb) / dist_
                upd = flat & (drop > bestdrop)
                bestdrop[upd] = drop[upd]; di[upd] = k
            # 合成梯度里仍有平手（等距等高）的残余格：再做一次多源 BFS 兜底，
            # 一律指向「离已定向格更近」的邻格。步数严格递减，故不成环。
            resid = flat & (di < 0)
            if resid.any():
                bfs = np.full((h, w), -1, np.int32)
                bfs[~resid] = 0
                cur = ~resid; k2 = 0
                while True:
                    k2 += 1
                    nxt = ndimage.binary_dilation(cur, K3) & resid & (bfs < 0)
                    if not nxt.any(): break
                    bfs[nxt] = k2; cur = nxt
                bfs[bfs < 0] = k2 + 1
                bpad = np.pad(bfs.astype(np.float64), 1, constant_values=np.inf)
                bkey = np.full((h, w), np.inf)
                for k, (dr, dc, _d) in enumerate(offs):
                    nb_b = bpad[1+dr:1+dr+h, 1+dc:1+dc+w]
                    nb_s = spad[1+dr:1+dr+h, 1+dc:1+dc+w]
                    key = nb_b * 1e6 + nb_s
                    upd = resid & (key < bkey) & (nb_b < bfs)
                    bkey[upd] = key[upd]; di[upd] = k
                # 兜底格的合成高程再抬一点，保证累积排序上它在下游之前
                synth = synth + 1e-6 * np.where(resid, bfs, 0)
        else:
            synth = fill.astype(np.float64)
        self.d8, self.offs = di, offs
        self.synth = synth
        # 累积：按合成高程降序单遍推流（平地上从远端推向出口）
        order = np.argsort(synth.ravel())[::-1]
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

def ramp(x, a, b):
    """软阈值：x 在 a 处为 0、b 处为 1，线性过渡（a>b 时为递减方向）。
    硬阈值会让擦线的点整份吃下 0.15-0.40 的折减，是分数跳变的来源之一。"""
    if a == b: return 1.0 if x >= a else 0.0
    return float(min(1.0, max(0.0, (x - a) / (b - a))))


def bearing_diff(b, ref):
    return (b - ref + 180) % 360 - 180

# ── 单点指标 ──────────────────────────────────────────────────
def metrics(reg, lat, lon, R=6000.0, theta_deg=None, scale=1.0):
    S = float(scale)                 # 尺度因子：所有分析环带按此缩放
    R = R * S                        # 窗口随之放大
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
    # v0.4 空间平滑：h0 取 60 m 邻域中位数，而非单像元。
    # 上限测试显示单像元取值是分数抖动的主因（±100m 位移下 SD=0.024，占效应 57%）。
    _c = dist <= 60
    h0 = float(np.median(h[_c])) if _c.sum() >= 4 else float(reg.sample([lat], [lon])[0])
    M = {}
    M["h0"] = h0
    r3 = (dist > 100) & (dist <= 3000)
    M["relief_3km"] = float(np.nanmax(h[r3]) - np.nanmin(h[r3])) if r3.any() else 0.0
    r6 = (dist > 100) & (dist <= R)
    M["relief_6km"] = float(np.nanmax(h[r6]) - np.nanmin(h[r6])) if r6.any() else 0.0

    # 坐山方向：0.3–2.5km 内高出穴部分的质量方向
    # 《葬经翼》「开面降势方名元武垂头」：来脉 = 上升最连贯、中途无凹断的方位
    rr_ = np.arange(0, 2401*S, 30.0*S)
    ths = np.arange(0, 360, 10.0)
    LA = lat + np.cos(np.radians(ths))[:, None] * rr_[None, :] / M_PER_DEG_LAT
    LO = lon + np.sin(np.radians(ths))[:, None] * rr_[None, :] / reg.mx
    P = reg.sample(LA.ravel(), LO.ravel()).reshape(len(ths), len(rr_))
    runm = np.maximum.accumulate(P, axis=1)
    broken = (runm - P) > 20.0                       # 凹断 >20 m 即视为脉断
    firstbrk = np.where(broken.any(1), broken.argmax(1), len(rr_))
    gain = np.array([runm[i, max(firstbrk[i] - 1, 0)] - h0 for i in range(len(ths))])
    if gain.max() < 30.0:                            # 平洋无脉可寻，退回高程质心
        band = (dist >= 300*S) & (dist <= 4000*S)
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
    def ang(mask, lo, hi, q=97.0):
        """仰角取 P97 而非 max —— max 由单个噪声像元决定，是抖动的第二大来源。"""
        m = mask & (dist >= lo) & (dist <= hi)
        if m.sum() < 20: return 0.0
        return float(np.percentile(np.degrees(np.arctan2(np.clip(h[m] - h0, 0, None), dist[m])), q))

    # R1 玄武垂头
    M["backing"] = sec(back, 300*S, 4000*S)
    prof_r = np.arange(0, 2001*S, 30.0*S)
    # 剖面沿 θ 及 θ±10° 三线平均，抑制单线采样抖动
    _p = []
    for _dt in (-10.0, 0.0, 10.0):
        _th = theta + _dt
        _la = lat + np.cos(math.radians(_th)) * prof_r / M_PER_DEG_LAT
        _lo = lon + np.sin(math.radians(_th)) * prof_r / reg.mx
        _p.append(reg.sample(_la, _lo))
    prof = np.mean(_p, axis=0)
    M["back_slope_near"] = float(np.degrees(np.arctan((prof[10] - prof[0]) / (300.0*S))))
    top = int(np.argmax(prof))                          # 靠山主峰在剖面上的位置
    seg = prof[:top + 1] if top >= 3 else prof[:4]
    run = np.maximum.accumulate(seg)
    M["back_dip"] = float(np.max(run - seg))            # 只量穴到主峰之间的凹断
    M["back_mono"] = float((np.diff(seg) >= -1.0).mean())
    M["back_top_m"] = float(top * 30.0 * S)
    M["back_rise_300"] = float(prof[10] - prof[0])

    # R2 龙虎
    # 贴身龙虎(形) 与 外龙虎/水口砂(势)：明十三陵龙山虎山在陵前 6 km，贴身砂仅数百米
    M["L_rise"], M["R_rise"] = sec(left, 200*S, 1200*S), sec(right, 200*S, 1200*S)
    M["L_ang"],  M["R_ang"]  = ang(left, 200*S, 1200*S), ang(right, 200*S, 1200*S)
    M["Lout"],   M["Rout"]   = sec(left, 2000*S, 6000*S), sec(right, 2000*S, 6000*S)
    # 折臂：左右各 8 个方位的仰角序列是否有深缺口
    gaps = []
    for base in ((theta + 90) % 360, (theta - 90) % 360):
        seq = []
        for k in range(-3, 4):
            b = (base + k * 12) % 360
            m = (np.abs(bearing_diff(brg, b)) <= 6) & (dist >= 200*S) & (dist <= 2000*S)
            seq.append(float(np.percentile(np.degrees(np.arctan2(np.clip(h[m]-h0,0,None), dist[m])),97)) if m.sum() > 5 else 0.0)
        seq = np.array(seq); med = np.median(seq)
        gaps.append(float((seq < med * 0.5).sum() / len(seq)) if med > 0.5 else 0.0)
    M["gap_ratio"] = max(gaps)

    # R3 向背
    gy, gx = np.gradient(h, RES * M_PER_DEG_LAT, RES * reg.mx)
    aN, aE = gy, -gx                      # 坡面下降方向（朝向低处）
    toN, toE = -dN / np.maximum(dist, 1), -dE / np.maximum(dist, 1)   # 指向穴
    dot = (aN * toN + aE * toE) / np.maximum(np.hypot(aN, aE), 1e-6)
    # 《葬经翼·四兽砂水篇》「不拘远近，俱名有情」——原文明言距离不论，故放宽环带
    ring2 = (dist >= 100*S) & (dist <= 4000*S)
    M["facing_ratio"] = float((dot[ring2] > 0).mean()) if ring2.sum() > 50 else 0.5

    # R4 明堂
    mf = front & (dist >= 100*S) & (dist <= 800*S)
    if mf.sum() > 20:
        gmag = np.degrees(np.arctan(np.hypot(gy, gx)))
        M["front_slope"] = float(np.mean(gmag[mf]))
        M["front_drop"] = h0 - float(np.median(h[mf]))
    else:
        M["front_slope"], M["front_drop"] = 20.0, -50.0
    M["front_open"] = ang(front, 200*S, 1200*S)
    M["an_ang"] = ang(front, 300*S, 2000*S)
    M["chao_ang"] = ang(front, 2000*S, 6000*S)
    of = front & (dist >= 2000*S) & (dist <= 6000*S)      # 案外大堂：规模宏阔
    M["outer_open"] = float(np.mean(np.degrees(np.arctan2(np.clip(h[of]-h0,0,None), dist[of])))) if of.sum() > 20 else 0.0

    # R8 藏风
    hs = ndimage.uniform_filter(h, size=3)      # 轻度低通，仅用于 TPI 与粗糙度
    near = dist <= 500*S
    M["tpi"] = h0 - float(np.mean(hs[near]))
    bar = []
    for k in range(36):
        b = k * 10.0
        m = (np.abs(bearing_diff(brg, b)) <= 5) & (dist >= 100*S) & (dist <= 3000*S)
        bar.append(float(np.percentile(np.degrees(np.arctan2(np.clip(h[m]-h0,0,None), dist[m])),97)) if m.sum() > 5 else 0.0)
    M["barrier"] = float((np.array(bar) > 2.0).mean())

    # F6 破面：坡面粗糙度
    M["tri"] = float(np.std(hs[(dist <= 300*S)]))
    # 地貌类型 —— 无定河实证中排第一位的因子（黄土丘陵密度 182.6 vs 山地 25.3
    # vs 洪积平原 18.9 处/10^4km²）。此处按 3km 起伏度 + 局部坡度 + 粗糙度粗分四类。
    loc = dist <= 1000*S
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
        m2 = (dist >= 300*S) & (dist <= 1500*S) & (np.abs(bearing_diff(brg, b)) <= 7.5)
        sg.append(1 if (m2.sum() > 5 and np.percentile(h[m2], 75) - h0 > 15) else 0)
    M["sand_gather"] = float(np.mean(sg))            # 群砂聚集
    # 独山：「气以龙会」，无过脉与外相连者不可葬
    # 判据：1.5–3 km 环带上，高于穴 30 m 的方位占比（有脉相连则不止一个方向高）
    rr2 = (dist >= 1500*S) & (dist <= 3000*S)
    conn = []
    for k in range(24):
        b = k * 15.0
        m2 = rr2 & (np.abs(bearing_diff(brg, b)) <= 7.5)
        conn.append(1 if (m2.sum() > 5 and np.percentile(h[m2], 75) - h0 > 30) else 0)
    M["ridge_conn"] = float(np.mean(conn))          # 独山 → 接近 0
    # 真龙「两水相夹送」：来龙方位两侧各 60° 内是否都有水道
    M["flank_water"] = 0.0

    # R6/R7 水
    M.update(_water(reg, lat, lon, h0, theta, S))
    M["flank_water"] = _flank_water(reg, lat, lon, theta, S)
    M["water_converge"] = _converge(reg, lat, lon, 2000.0*S)
    M.update(_mingtang_water(reg, lat, lon, h0, theta, S,
                             known=(theta_deg is not None)))
    M.update(_pingyang(reg, lat, lon, h0, S))       # v0.8：平洋法（《水龙经》）
    return M


# ── B7 平洋法 ──《欽定古今圖書集成》卷 671–674《水龍經》──────────────
# 立这一节的理由：此前 16 条规则全部出自山龙一系，而《水龙经》开篇即说
# 「後世言地，知山之龍而不知水之龍，遂使平洋水局之地，傅會山龍之妄說」——
# 拿山龙判据去评平原，原文自己就点名说是错的。洛阳盆地、关中、陆家嘴都是平原样本。
def _pingyang(reg, lat, lon, h0, S=1.0):
    """《水龍經》平洋法。四项，出处逐条注在下面。

    支幹排第一有原文依据：「余以支幹之說，為水龍第一義」（卷671 總論一）。
    其余三项之间的权重是估值，原文只给了「水龍妙用，只在流神曲秀」这一句偏重。
    """
    out = {"py_zhigan": 0.0, "py_class": "俱無", "py_wrap": 0.0,
           "py_bends": 0, "py_grad": 999.0, "py": 0.0,
           "py_zhi_d": 9999.0, "py_gan": 0.0, "py_zhi": 0.0}
    if reg.stream_rc.size == 0:
        out.update(py_class="不判(无水系数据)", py=None, py_zhigan=None)
        return out
    cr, cc = reg.crc(lat, lon)
    dy = (reg.stream_rc[:, 0] - cr) * reg.cdy
    dx = (reg.stream_rc[:, 1] - cc) * reg.cdx
    d = np.hypot(dx, dy)
    near = d < 4000 * S
    if not near.any():
        out.update(py_class="不判(4km 内无水道)", py=None, py_zhigan=None)
        return out
    idx = np.argwhere(near).ravel()
    acc = np.array([reg.acc_km2[r, c] for r, c in reg.stream_rc[idx]])
    amax = float(acc.max())
    if amax <= 0:
        out.update(py_class="不判(汇水面积为零)", py=None, py_zhigan=None)
        return out

    # ① 支幹相扶 ——「以通流大水為行龍而為幹，溝渠小水為割界而為支。穴法取支不取幹」
    #   「大江大河……其氣曠渺，與墓宅不親，斷難下手。須於其旁另有支水，作元辰繞抱成胎」
    # 判不了就不判。DEM 汇流网络在平原上严重低估干流：本项目实测洛阳一带
    # 4 km 内最大汇水仅 20 余 km²，而洛河实际流域上万 km²——120 m 重采样加填洼
    # 根本分辨不出宽浅的大河河槽。此时「幹」与「支」无从区分，
    # 报「俱無」就是拿「没检测到」冒充「没有」，与明堂水项同一类错误，故不判。
    STREAM_THR = 2.0                             # Region._drainage 的成道阈值
    if amax < 4 * STREAM_THR:
        out.update(py_class="不判(汇流网络未见干水)", py=None, py_zhigan=None)
        return out
    gan_thr = max(4 * STREAM_THR, 0.30 * amax)  # 幹：通流大水
    zhi_thr = 0.25 * amax                        # 支：溝渠小水
    is_gan = acc >= gan_thr
    has_gan = bool(is_gan.any())
    zhi_m = (acc <= zhi_thr) & (d[idx] < 1000 * S)                   # 支须在「旁」
    has_zhi = bool(zhi_m.any())
    # 支到穴的距离——「須於其旁另有支水，作元辰繞抱成胎」，越贴身越是「內氣」
    out["py_zhi_d"] = float(d[idx][zhi_m].min()) if has_zhi else 9999.0
    if has_gan and has_zhi:
        # 「皆不若支幹相扶之地也」
        out.update(py_zhigan=1.00, py_class="支幹相扶")
    elif has_gan or has_zhi:
        # 「小幹無支，其局雖大，必久而後發；支龍無幹，其效雖捷，而氣盡易衰」
        # 原文没有把这两者互相排序，故给同值，不臆造高下。
        out.update(py_zhigan=0.40,
                   py_class="有幹無支" if has_gan else "有支無幹")

    # ② 幹水回頭環繞 ——「大江大河一二十里而來，不見回頭環繞，中間雖有屈曲，
    #   決不結穴，直至環轉回顧之處，方是龍脈止聚」
    if has_gan:
        gaz = np.degrees(np.arctan2(dx[idx][is_gan], dy[idx][is_gan])) % 360.0
        occ = np.zeros(24, bool)
        occ[(gaz // 15).astype(int)] = True
        out["py_wrap"] = float(occ.mean())

    # ③④ 沿最近河道上下游各走约 1.2 km，量「屈曲」与「停蓄」
    i0 = idx[int(np.argmin(d[idx]))]
    pr, pc = reg.stream_rc[i0]
    pts = [(pr, pc)]
    r, c = pr, pc
    for _ in range(12):                                   # 下游
        k = reg.d8[r, c]
        if k < 0: break
        r, c = r + reg.offs[k][0], c + reg.offs[k][1]
        if not (0 <= r < reg.d8.shape[0] and 0 <= c < reg.d8.shape[1]): break
        pts.append((r, c))
    up, r, c = [], pr, pc
    for _ in range(12):                                   # 上游取汇流最大者
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
    chan = list(reversed(up)) + pts
    if len(chan) >= 5:
        P = np.array([[q[1] * reg.cdx, -q[0] * reg.cdy] for q in chan])
        v = np.diff(P, axis=0)
        cross = v[:-1, 0] * v[1:, 1] - v[:-1, 1] * v[1:, 0]     # 转向的正负
        sgn = np.sign(cross[np.abs(cross) > 1e-6])
        # ③「水法不拘去與來，但要屈曲去復迴，三回五度轉顧穴」——数的是转向反复的次数
        out["py_bends"] = int((np.diff(sgn) != 0).sum()) if sgn.size > 1 else 0
        # ④「澄清停蓄甚為佳，傾瀉急流有何益」——河道纵比降，越平越「停蓄」
        hs = np.array([reg.fill[q[0], q[1]] for q in chan], float)
        L = float(np.hypot(*v.T).sum())
        if L > 1:
            out["py_grad"] = float(abs(hs[0] - hs[-1]) / (L / 1000.0))

    # 势/形在平洋的对应物：「以幹龍繞抱，取外氣形局；以支龍正息交會，取內氣孕育」
    # ——幹即势（外气），支即形（内气）。这不是我的类比，是卷 671 總論一的原话。
    out["py_gan"] = pl(out["py_wrap"], [(0,0),(.15,.35),(.35,.8),(.6,1)])
    out["py_zhi"] = pl(out["py_zhi_d"], [(0,1),(400,1),(1000,.5),(2000,.15),(9999,0)])

    out["py"] = (.40 * out["py_zhigan"]
               + .25 * pl(float(out["py_bends"]), [(0,.15),(1,.45),(3,1),(5,1),(12,1)])
               + .20 * pl(out["py_wrap"], [(0,0),(.15,.35),(.35,.8),(.6,1)])
               + .15 * pl(out["py_grad"], [(0,1),(2,.9),(10,.4),(30,.1),(100,0)]))
    return out

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


def _flank_water(reg, lat, lon, theta, S=1.0):
    """《寻龙》真龙气脉必有两水相夹送：来龙轴线左右两侧 3 km 内是否各有水道。"""
    if reg.stream_rc.size == 0: return 0.0
    cr, cc = reg.crc(lat, lon)
    dy = (reg.stream_rc[:, 0] - cr) * reg.cdy * -1.0
    dx = (reg.stream_rc[:, 1] - cc) * reg.cdx
    d = np.hypot(dx, dy)
    sel = d < 3000*S
    if sel.sum() == 0: return 0.0
    b = (np.degrees(np.arctan2(dx[sel], dy[sel]))) % 360
    rel = (b - theta + 180) % 360 - 180
    left  = ((rel > 20) & (rel < 160)).any()
    right = ((rel < -20) & (rel > -160)).any()
    return float(left) * 0.5 + float(right) * 0.5


def _mingtang_water(reg, lat, lon, h0, theta, S=1.0, known=True):
    """《葬经翼·明堂篇》：「明堂者，穴前水聚处也」
       「大抵明堂以聚水为上，横抱次之，朝水又次之，
         交互有情、不见水去而顺流者又次之。」
       原文给的是**有序**四级，不是并列加权，故此处返回序位分而非加权和。"""
    # 坐向未知则不判。「穴前」是相对于向的方位，向若靠地形反推而来，
    # 本项就无意义——此时返回 None，由 score() 把该项排除并重新归一，
    # 而不是给 0 分（那就是拿「没检测到」冒充「没有」）。
    out = {"mt_water": None, "mt_class": "不判(坐向未知)"}
    if not known:
        return out
    out = {"mt_water": 0.0, "mt_class": "无水"}
    if reg.stream_rc.size == 0:
        out.update(py_class="不判(无水系数据)", py=None, py_zhigan=None)
        return out
    cr, cc = reg.crc(lat, lon)
    dy = (reg.stream_rc[:, 0] - cr) * reg.cdy * -1.0
    dx = (reg.stream_rc[:, 1] - cc) * reg.cdx
    d = np.hypot(dx, dy)
    xiang = (theta + 180.0) % 360.0                      # 向 = 坐 + 180
    az = np.degrees(np.arctan2(dx, dy)) % 360.0
    front = (np.abs(bearing_diff(az, xiang)) <= 45) & (d > 80 * S) & (d < 1500 * S)
    if not front.any():
        return out
    idx = np.argwhere(front).ravel()
    accs = np.array([reg.acc_km2[r, c] for r, c in reg.stream_rc[idx]])
    i_near = idx[int(np.argmin(d[idx]))]
    pr, pc = reg.stream_rc[i_near]
    a_near = float(reg.acc_km2[pr, pc])

    # 「聚水」：前方水量显著大于最近一条，或前方扇区内有支流交汇
    gather = (accs.max() >= max(2.0 * a_near, a_near + 0.5)) if a_near > 0 else (accs.max() > 0.5)

    # 水流方向（D8）与「水→穴」方向的夹角
    k = reg.d8[pr, pc]
    if k >= 0:
        orr, occ = reg.offs[k][0], reg.offs[k][1]
        fv_n, fv_e = -orr * reg.cdy, occ * reg.cdx
        flow_az = math.degrees(math.atan2(fv_e, fv_n)) % 360.0
        to_site = (math.degrees(math.atan2(-dx[i_near], -dy[i_near]))) % 360.0
        ang = abs(bearing_diff(flow_az, to_site))
    else:
        ang = 90.0

    if gather:
        out.update(mt_water=1.00, mt_class="聚水")
    elif 60 <= ang <= 120:
        out.update(mt_water=0.75, mt_class="横抱")
    elif ang < 60:
        out.update(mt_water=0.50, mt_class="朝水")
    else:
        out.update(mt_water=0.25, mt_class="顺流")
    return out

def _water(reg, lat, lon, h0, theta, S=1.0):
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
    dm = d < 1500*S
    if dm.any():
        out["river_km2"] = float(max(reg.acc_km2[r, c] for r, c in reg.stream_rc[dm]))
    if d[i] > 6000*S: return out
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
# v0.8 平洋权重改按《水龙经》重排。原 W_PLAIN 只是把山龙各项按比例调了调，
# 而原文说的是山龙判据在平洋根本不适用：
#   「行到平洋莫問蹤，只看水繞是真龍」
#   「平陽大地無龍虎，漭漭歸何處？東西只取水為龍」（卷671 序）
# 故平洋模式下 xuanwu 与 hulong 归零，其 0.14 全部转给 pingyang。
# 藏风保留 0.03——《水龙经》未论藏风，不能借它的名义删《葬经》的条目。
W_PLAIN = dict(water=.34, water_gate=.14, mingtang=.22, xuanwu=.00, hulong=.00,
               xiangbei=.13, zangfeng=.03, pingyang=.14)

def score(M):
    """《葬经》「千尺为势，百尺为形，势与形顺者吉，势与形逆者凶。
    势凶形吉，百福希一。势吉形凶，祸不旋日」——势与形是乘性关系，不是加权和。"""
    if M is None: return None
    c = {}
    c["xuanwu"] = .45*pl(M["backing"], [(-50,0),(0,.12),(50,1),(300,1),(800,.55),(1500,.3)]) \
                + .30*pl(M["back_slope_near"], [(0,.2),(3,.8),(8,1),(20,1),(30,.5),(45,.1)]) \
                + .25*pl(M["back_mono"], [(.5,0),(.75,.5),(.92,1)])
    # 龙虎双尺度：贴身砂(形) 七成，外龙虎/水口砂(势) 三成
    # v0.7：删去左右对称项。《葬经翼·四兽砂水篇》对龙虎的要求是
    # 「环抱有情，不逼不压，不折不窜」，并「青龙蜿蜒，白虎驯頫」——
    # 给左右规定了不同形态，全文无一处要求对称。原对称项占 hulong 24.5%，无出处，删。
    near_hu = .60*pl(min(M["L_rise"], M["R_rise"]), [(-30,0),(0,.25),(30,.8),(120,1),(500,1)]) \
            + .40*pl(max(M["L_ang"], M["R_ang"]), [(0,.4),(5,1),(18,1),(30,.3),(45,0)])
    out_hu  = pl(min(M["Lout"], M["Rout"]), [(-100,0),(0,.3),(50,.7),(200,1),(900,1)])
    c["hulong"] = .70*near_hu + .30*out_hu
    c["xiangbei"] = pl(M["facing_ratio"], [(.30,0),(.50,.40),(.65,.85),(.80,1)])
    # 明堂两层：案内明堂 + 案外大堂（清东陵相度档案「案内明堂舒畅开阳，案外大堂规模宏阔」）
    # v0.7：补入水项。《葬经翼·明堂篇》「明堂者，穴前水聚处也」，
    # 且「以聚水为上，横抱次之，朝水又次之，……顺流者又次之」——
    # 明堂在原文里首先是水的形态，此前六个分项全是地形，一项水都没有。
    # 水项权重 .35，其余三项按原比例压缩至 .65。
    _terr = (.30*pl(M["front_slope"], [(0,1),(6,1),(15,.4),(30,0)])
           + .25*pl(M["front_drop"], [(-50,0),(0,.5),(10,1),(150,1)])
           + .45*pl(M["front_open"], [(0,.45),(1,.8),(3,1),(8,.7),(15,.25),(25,0)]))
    _mtw = M.get("mt_water")
    if _mtw is None:
        inner = _terr                      # 坐向未知：水项不判，退回纯地形并保持归一
    else:
        inner = .35*_mtw + .65*_terr
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
    W = dict(W_PLAIN if mode == "plain" else W_MOUNT)
    _py = M.get("py")
    if mode == "plain":
        if _py is None:
            # 平洋项不判：把它的权重按比例摊回其余各项，而不是记 0 分。
            # 同 mingtang 水项的处理——「没检测到」不等于「没有」。
            w_py = W.pop("pingyang")
            rest = sum(W.values())
            for k in W: W[k] = W[k] * (1 + w_py / rest)
        else:
            c["pingyang"] = float(_py)
    for k in W: c[k] = min(max(c[k], 0), 1)

    # ── 势 与 形 ──────────────────────────────────────────────
    # 势(千尺)：玄武、外龙虎/外堂、水口关锁；形(百尺)：内明堂、贴身龙虎、得水、向背
    # v0.8：平洋的势与形换成水的对应物。《水龙经》卷671 總論一：
    # 「以幹龍繞抱，取外氣形局；以支龍正息交會，取內氣孕育」——
    # 幹即势（外气），支即形（内气）。在平原上拿玄武充势、拿贴身龙虎充形，
    # 正是原文批的「傅會山龍之妄說」。
    if mode == "plain" and _py is not None:
        shi  = (.45*M.get("py_gan", 0.0) + .25*outer + .30*c["water_gate"])
        xing = (.35*inner + .30*M.get("py_zhi", 0.0) + .20*c["water"] + .15*c["xiangbei"])
    else:
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
    def add(name, pen, r):
        if r > 0.02: F[name] = pen * r
    add("拒尸(玄武不垂)", .40, ramp(M["back_dip"], 25, 60))
    if M["bank"] < 0 and M["d_water"] < 800:
        add("朱雀腾去", .40, ramp(M["sinuosity"], 1.08, 1.30))
    add("虎蹲(衔尸)", .35, ramp(M["R_ang"], 25, 38))
    add("龙踞(嫉主)", .35, ramp(M["L_ang"], 25, 38))
    add("断山(坠足)", .25, ramp(M["back_rise_300"], 110, 200))
    if mode == "mountain":
        if M.get("water_converge", 1) < 1:
            add("过山(势未止)", .30, ramp(M.get("sand_gather", 1), .35, .12))
        add("独山(气不会)", .35, ramp(M.get("ridge_conn", 1), .25, .06))
    else:
        # 《水龍經·幹水散氣圖說》：「幹水斜行，似有曲折，而非環抱，
        # 又無支水，以作內氣，總不結穴。」——三个条件同时成立才算，
        # 且原文说的是「總不結穴」，属门槛级，故罚重（与五不葬同量级）。
        if (M.get("py") is not None and M.get("py_class") == "有幹無支"
                and M.get("py_wrap", 1.0) < 0.35):
            add("干水散气", .35, ramp(M.get("py_wrap", 1.0), .35, .10))
    add("折臂", .15, ramp(M["gap_ratio"], .20, .42))
    add("割脚", .20, ramp(M["d_water"], 80, 25))
    disc = 1.0
    for v in F.values(): disc *= (1 - v)
    return dict(components=c, mode=mode, base=base, shi=shi, xing=xing,
                mismatch=mism, faults=F, final=base*mism*disc)
