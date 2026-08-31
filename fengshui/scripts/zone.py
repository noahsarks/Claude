"""区域口径验证：不比"这个点"，比"这个点周围有没有高分区"。
   每个点取 中心 + 6 个 1.2km 环上采样，共 7 个样本，用最大值代表该点所在小区域。
   坐标误差 1.3km 时，真实穴场几乎必落在这个邻域内 —— 这正是用户提的口径。"""
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
RNG=np.random.default_rng(20260831)
RING_R=1200.0; RING_N=6; N_BG=800

REGIONS=[("京津冀",range(39,41),range(115,118)),
         ("晋南豫北",range(34,37),range(112,115)),
         ("关中",range(34,35),range(107,110))]

def zone(reg, la, lo):
    """返回 (点分, 邻域最大分, 邻域中位分)"""
    vs=[]
    s=L.score(L.metrics(reg,la,lo))
    if s is None: return None
    pt=s['final']; vs.append(pt)
    for k in range(RING_N):
        th=k*360.0/RING_N
        a=la+math.cos(math.radians(th))*RING_R/L.M_PER_DEG_LAT
        b=lo+math.sin(math.radians(th))*RING_R/reg.mx
        s2=L.score(L.metrics(reg,a,b))
        if s2: vs.append(s2['final'])
    v=np.array(vs)
    return pt, float(v.max()), float(np.median(v))

def kv(area,site): return 1-area/site if site>0 else float('-inf')

REP=[]
for nm,lats,lons in REGIONS:
    reg=K.Mosaic(nm,lats,lons)
    mg=0.075
    POS=json.load(open(f'out/pos_{nm}.json'))
    BGold=json.load(open(f'out/bg_{nm}.json'))
    pos=[p for p in POS if reg.lat0+mg<p['lat']<reg.lat1-mg and reg.lon0+mg<p['lon']<reg.lon1-mg]
    bgp=[b for b in BGold if reg.lat0+mg<b['lat']<reg.lat1-mg and reg.lon0+mg<b['lon']<reg.lon1-mg][:N_BG]
    print(f"[{nm}] 正样本 {len(pos)}  背景 {len(bgp)}",flush=True)
    P=[]
    for p in pos:
        z=zone(reg,p['lat'],p['lon'])
        if z: P.append(dict(k=p['k'],name=p['name'],pt=z[0],zmax=z[1],zmed=z[2]))
    print(f"  正样本邻域完成 {len(P)}",flush=True)
    B=[]
    for b in bgp:
        z=zone(reg,b['lat'],b['lon'])
        if z: B.append(dict(pt=z[0],zmax=z[1],zmed=z[2]))
    print(f"  背景邻域完成 {len(B)}",flush=True)
    del reg
    json.dump(dict(pos=P,bg=B),open(f'out/zone_{nm}.json','w'),ensure_ascii=False,default=float)
    row={'region':nm}
    for stat in ('pt','zmax','zmed'):
        bs=np.array([x[stat] for x in B])
        th80=np.percentile(bs,80)
        for kind in ('all','tomb','building'):
            Q=P if kind=='all' else [x for x in P if x['k']==kind]
            if len(Q)<8: continue
            ps=np.array([x[stat] for x in Q])
            auc=float(np.mean([(bs<v).mean()+.5*(bs==v).mean() for v in ps]))
            hi=100*float((ps>=th80).mean())
            row[f'{stat}_{kind}']=dict(n=len(Q),auc=auc,site_hi=hi,gain=kv(20,hi),mean=float(ps.mean()),bg=float(bs.mean()))
    REP.append(row)
    print(f"  点口径 AUC(all)={row.get('pt_all',{}).get('auc',float('nan')):.3f}  "
          f"区域口径 AUC(all)={row.get('zmax_all',{}).get('auc',float('nan')):.3f}",flush=True)
json.dump(REP,open('out/zone_summary.json','w'),ensure_ascii=False,indent=1,default=float)
print("\n=== 汇总：点口径 vs 区域口径 ===")
for r in REP:
    print(f"\n{r['region']}")
    print(f"{'类别':10s}{'n':>5s}{'点AUC':>9s}{'区域AUC':>9s}{'点增益':>9s}{'区域增益':>10s}")
    for kind in ('all','tomb','building'):
        a=r.get(f'pt_{kind}'); b=r.get(f'zmax_{kind}')
        if not a: continue
        print(f"{kind:10s}{a['n']:5d}{a['auc']:9.3f}{b['auc']:9.3f}{a['gain']:9.3f}{b['gain']:10.3f}")
