"""尺度扫描：都城选址是否在更大的势尺度上才显现。"""
import sys, json, math, numpy as np, multiprocessing as mp
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
BOX=(34.52,34.88,112.20,112.88)
reg=None
def init():
    global reg; reg=K.Mosaic('洛阳',range(34,35),range(112,113))
def job(t):
    la,lo,S=t
    try:
        r=L.score(L.metrics(reg,la,lo,scale=S)); return r['final'] if r else np.nan
    except Exception: return np.nan
if __name__=="__main__":
    S=[s for s in json.load(open('guobao.json')) if BOX[0]<s['lat']<BOX[1] and BOX[2]<s['lon']<BOX[3]]
    S+=[{"name":"汉魏洛阳故城*","lat":34.7256,"lon":112.5747},{"name":"偃师商城*","lat":34.7167,"lon":112.7833}]
    RNG=np.random.default_rng(7)
    mg=0.10
    BG=[(RNG.uniform(BOX[0]+mg,BOX[1]-mg),RNG.uniform(BOX[2]+mg,BOX[3]-mg)) for _ in range(500)]
    S=[x for x in S if BOX[0]+mg<x['lat']<BOX[1]-mg and BOX[2]+mg<x['lon']<BOX[3]-mg]
    print(f"古迹 {len(S)} 处（去掉近边缘者），背景 {len(BG)}",flush=True)
    res={}
    for sc in (1.0,2.0,3.0):
        with mp.Pool(3,initializer=init) as p:
            sv=np.array(p.map(job,[(x['lat'],x['lon'],sc) for x in S]),dtype=float)
            bv=np.array(p.map(job,[(a,b,sc) for a,b in BG]),dtype=float)
        m=np.isfinite(sv); bv=bv[np.isfinite(bv)]
        th=np.percentile(bv,80)
        hi=100*float((sv[m]>=th).mean())
        auc=float(np.mean([(bv<v).mean()+.5*(bv==v).mean() for v in sv[m]]))
        res[sc]=dict(auc=auc,site_hi=hi,gain=(1-20.0/hi if hi>0 else None),
                     scores={x['name']:(float(v) if np.isfinite(v) else None) for x,v in zip(S,sv)})
        g=res[sc]['gain']
        print(f"尺度 {sc:.0f}x (势 {6*sc:.0f} km / 形 {2*sc:.0f} km): AUC={auc:.3f}  落入前20%={hi:.1f}%  增益={g:+.3f}" if g is not None
              else f"尺度 {sc:.0f}x: AUC={auc:.3f} 落入前20%=0",flush=True)
    json.dump(res,open('out/scalescan.json','w'),ensure_ascii=False,indent=1,default=float)
    KEY=['二里頭遺址','隋唐洛阳城遗址','东周王城','汉魏洛阳故城*','偃师商城*','白马寺','关林','洛南东汉帝陵','恭陵']
    print(f"\n{'古迹':18s}{'1x':>8s}{'2x':>8s}{'3x':>8s}")
    for k in KEY:
        v=[res[s]['scores'].get(k) for s in (1.0,2.0,3.0)]
        if any(x is None for x in v): continue
        print(f"{k[:16]:18s}{v[0]:8.3f}{v[1]:8.3f}{v[2]:8.3f}")
