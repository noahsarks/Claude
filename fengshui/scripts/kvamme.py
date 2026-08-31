"""大样本验证：国保单位 vs 随机背景，报 Kvamme 增益。"""
import sys, json, math, glob, re, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as L

RNG=np.random.default_rng(20260831)
N_BG=3000

REGIONS=[  # (名称, 瓦片纬度范围, 瓦片经度范围)
 ("京津冀 燕山南麓", range(39,41), range(115,118)),
 ("晋南豫北 太行王屋", range(34,37), range(112,115)),
 ("关中 渭河两岸",     range(34,35), range(107,110)),
]

def cls(n):
    if any(k in n for k in ['群','十三陵','陵区']): return 'ensemble'
    if any(k in n for k in ['墓','陵','冢','坟']):   return 'tomb'
    if any(k in n for k in ['寺','庙','塔','祠','观','宫','书院','故居','民居','村','楼','阁']): return 'building'
    return 'other'

class Mosaic(L.Region):
    """按瓦片范围直接拼，不用中心+pad。"""
    def __init__(self, name, lats, lons, coarse=4):
        self.name=name
        rows=sorted(lats, reverse=True); cols=sorted(lons)
        self.clat=(min(lats)+max(lats)+1)/2; self.clon=(min(lons)+max(lons)+1)/2
        import rasterio
        blocks=[]
        for r in rows:
            row=[]
            for c in cols:
                p=L._TILES.get((r,c))
                if p is None: row.append(np.full((3600,3600),np.nan,np.float32)); continue
                with rasterio.open(p) as s: row.append(s.read(1).astype(np.float32))
            blocks.append(np.hstack(row))
        self.arr=np.vstack(blocks)
        self.west=min(cols)-(1/7200); self.north=max(rows)+1+(1/7200)
        self.arr[self.arr<-400]=np.nan
        self._filled=np.nan_to_num(self.arr,nan=0.0)
        self.mx=L.M_PER_DEG_LAT*math.cos(math.radians(self.clat))
        self.lat0,self.lat1=min(lats),max(lats)+1
        self.lon0,self.lon1=min(cols),max(cols)+1
        self._drainage(coarse)

def run(name, lats, lons, sites):
    reg=Mosaic(name,lats,lons)
    mg=0.06   # 6 km 边距（度），保证分析窗完整
    inr=lambda la,lo: (reg.lat0+mg<la<reg.lat1-mg) and (reg.lon0+mg<lo<reg.lon1-mg)
    pos=[s for s in sites if inr(s['lat'],s['lon'])]
    print(f"[{name}] 正样本 {len(pos)} 处 (tomb {sum(1 for s in pos if s['k']=='tomb')}, building {sum(1 for s in pos if s['k']=='building')})",flush=True)
    # 背景
    bg=[]
    while len(bg)<N_BG:
        la=RNG.uniform(reg.lat0+mg,reg.lat1-mg); lo=RNG.uniform(reg.lon0+mg,reg.lon1-mg)
        r,c=reg.rc(la,lo)
        if not np.isfinite(reg.arr[int(r),int(c)]): continue
        bg.append((la,lo))
    def rec(la,lo,kind,name=''):
        M=L.metrics(reg,la,lo)
        if M is None: return None
        s=L.score(M)
        if s is None: return None
        return dict(lat=la,lon=lo,k=kind,name=name,score=s['final'],mode=s['mode'],
                    h=M['h0'],relief=M['relief_3km'],comp=s['components'],faults=list(s['faults']))
    BG=[r for r in (rec(a,b,'bg') for a,b in bg) if r]
    print(f"  背景 {len(BG)} 点完成",flush=True)
    POS=[r for r in (rec(s['lat'],s['lon'],s['k'],s['name']) for s in pos) if r]
    print(f"  正样本 {len(POS)} 点完成",flush=True)
    del reg
    return np.array([r['score'] for r in BG]), [(r['score'],r['k']) for r in POS], BG, POS

def gain(bgs, vals, qs=(95,80,55,25)):
    """分位阈值由背景定 → %面积按构造已知；返回各级的 %遗址与增益。"""
    th=[np.percentile(bgs,q) for q in qs]
    def grade(v):
        for i,t in enumerate(th):
            if v>=t: return i+1
        return 5
    area=[5,15,25,30,25]                      # 由分位构造
    gs=[grade(v) for v in vals]
    out=[]
    for i in range(5):
        ps=100*sum(1 for g in gs if g==i+1)/max(len(gs),1)
        out.append((i+1,area[i],ps, (1-area[i]/ps) if ps>0 else float('-inf')))
    # 累计 I+II
    pa=area[0]+area[1]; pss=100*sum(1 for g in gs if g<=2)/max(len(gs),1)
    return out,(pa,pss,1-pa/pss if pss>0 else float('-inf')),th

if __name__=="__main__":
    S=[dict(lat=r['lat'],lon=r['lon'],name=r['name'],k=cls(r['name']))
       for r in json.load(open('guobao.json')) if 17<r['lat']<54 and 73<r['lon']<136]
    S=[s for s in S if s['k'] in ('tomb','building')]
    print("可用正样本(全国, 陵墓+建筑):",len(S))
    REP=[]
    for nm,la,lo in REGIONS:
        if not all(L._TILES.get((r,c)) for r in la for c in lo):
            print(f"[{nm}] 瓦片不全，跳过"); continue
        bgs,poss,BG,POS=run(nm,la,lo,S)
        vals=[v for v,_ in poss]
        rows,cum,th=gain(bgs,vals)
        auc=float(np.mean([np.mean(bgs<v)+0.5*np.mean(bgs==v) for v in vals]))
        # 蒙特卡洛：从背景随机抽同样多的点，看 I+II 增益分布
        mc=[]
        for _ in range(200):
            samp=RNG.choice(bgs,size=len(vals),replace=False)
            _,c2,_=gain(bgs,list(samp)); mc.append(c2[2])
        tag=nm.split()[0]
        json.dump(BG, open(f'out/bg_{tag}.json','w'), ensure_ascii=False, default=float)
        json.dump(POS, open(f'out/pos_{tag}.json','w'), ensure_ascii=False, default=float)
        REP.append(dict(region=nm,n_pos=len(vals),n_bg=len(bgs),rows=rows,cum=cum,auc=auc,
                        mc_mean=float(np.mean(mc)),mc_p95=float(np.percentile(mc,95)),
                        by_kind={k:float(np.mean([v for v,kk in poss if kk==k])) for k in ('tomb','building')},
                        bg_mean=float(bgs.mean()),pos_mean=float(np.mean(vals))))
        print(f"  全部 n={len(vals)}  AUC={auc:.3f}  I+II 增益={cum[2]:.3f} (随机 {np.mean(mc):+.3f}, P95 {np.percentile(mc,95):+.3f})",flush=True)
        for k in ('tomb','building'):
            vk=[v for v,kk in poss if kk==k]
            if len(vk)<8: print(f"    {k}: n={len(vk)} 太少，跳过"); continue
            _,ck,_=gain(bgs,vk)
            ak=float(np.mean([np.mean(bgs<v)+0.5*np.mean(bgs==v) for v in vk]))
            print(f"    {k}: n={len(vk)}  AUC={ak:.3f}  I+II 增益={ck[2]:.3f}  均分={np.mean(vk):.3f}",flush=True)
    json.dump(REP,open('out/kvamme.json','w'),ensure_ascii=False,indent=1,default=float)
    print("saved")
