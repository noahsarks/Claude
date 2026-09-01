"""洛阳盆地 3x 尺度分级图（势 18 km / 形 6 km），步长 800 m。"""
import sys, json, math, numpy as np, multiprocessing as mp
sys.path.insert(0, '/home/user/fs')
import luantou as L, kvamme as K

BOX = (34.52, 34.88, 112.20, 112.88)
STEP = 800.0
SCALE = 3.0
reg = None


def init():
    global reg
    reg = K.Mosaic('洛阳', range(34, 35), range(112, 113))


def cell(t):
    la, lo = t
    try:
        s = L.score(L.metrics(reg, la, lo, scale=SCALE))
        return s['final'] if s else np.nan
    except Exception:
        return np.nan


if __name__ == "__main__":
    nlat = int((BOX[1] - BOX[0]) * L.M_PER_DEG_LAT / STEP)
    mx = L.M_PER_DEG_LAT * math.cos(math.radians((BOX[0] + BOX[1]) / 2))
    nlon = int((BOX[3] - BOX[2]) * mx / STEP)
    lats = np.linspace(BOX[1], BOX[0], nlat)
    lons = np.linspace(BOX[2], BOX[3], nlon)
    print(f"格网 {nlat}x{nlon}={nlat*nlon} 点，步长 {STEP:.0f} m，尺度 {SCALE:.0f}x", flush=True)
    with mp.Pool(4, initializer=init) as p:
        vals = p.map(cell, [(a, b) for a in lats for b in lons], chunksize=16)
    G = np.array(vals, dtype=np.float32).reshape(nlat, nlon)
    np.save('out/luoyang3x_grid.npy', G)
    json.dump(dict(box=BOX, step=STEP, scale=SCALE, nlat=nlat, nlon=nlon,
                   lats=lats.tolist(), lons=lons.tolist()),
              open('out/luoyang3x_meta.json', 'w'))
    print(f"完成，有效 {np.isfinite(G).sum()}/{G.size}，区间 {np.nanmin(G):.3f}-{np.nanmax(G):.3f}")
