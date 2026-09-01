"""洛阳盆地分级图：先对全域格网评分分级，再看古建落在哪一级。"""
import sys, json, math, numpy as np, multiprocessing as mp
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K

BOX=(34.52,34.88,112.20,112.88)     # lat0,lat1,lon0,lon1
STEP=500.0                          # m
reg=None
def init():
    global reg
    reg=K.Mosaic('洛阳',range(34,35),range(112,113))
def cell(t):
    la,lo=t
    try:
        s=L.score(L.metrics(reg,la,lo))
        return s['final'] if s else np.nan
    except Exception:
        return np.nan
if __name__=="__main__":
    nlat=int((BOX[1]-BOX[0])*L.M_PER_DEG_LAT/STEP)
    mx=L.M_PER_DEG_LAT*math.cos(math.radians((BOX[0]+BOX[1])/2))
    nlon=int((BOX[3]-BOX[2])*mx/STEP)
    lats=np.linspace(BOX[1],BOX[0],nlat)      # 北→南
    lons=np.linspace(BOX[2],BOX[3],nlon)
    print(f"格网 {nlat} x {nlon} = {nlat*nlon} 个格点，步长 {STEP:.0f} m",flush=True)
    pts=[(a,b) for a in lats for b in lons]
    with mp.Pool(3,initializer=init) as p:
        vals=p.map(cell,pts,chunksize=64)
    G=np.array(vals,dtype=np.float32).reshape(nlat,nlon)
    np.save('out/luoyang_grid.npy',G)
    json.dump(dict(box=BOX,step=STEP,nlat=nlat,nlon=nlon,
                   lats=lats.tolist(),lons=lons.tolist()),
              open('out/luoyang_meta.json','w'))
    ok=np.isfinite(G)
    print(f"完成，有效格点 {ok.sum()}／{G.size}，分数区间 {np.nanmin(G):.3f}–{np.nanmax(G):.3f}，均值 {np.nanmean(G):.3f}")
