"""都城是盆地尺度的选址？把势尺度从 6 km 放到 20 km 重测洛阳。"""
import sys, json, math, numpy as np, multiprocessing as mp
sys.path.insert(0,'/home/user/fs'); import luantou as L, kvamme as K
BOX=(34.52,34.88,112.20,112.88)
reg=None
def init():
    global reg; reg=K.Mosaic('洛阳',range(34,35),range(112,113))
def job(t):
    la,lo,R=t
    try:
        s=L.score(L.metrics(reg,la,lo,R=R))
        return s['final'] if s else np.nan
    except Exception:
        return np.nan
if __name__=="__main__":
    S=[s for s in json.load(open('guobao.json')) if BOX[0]<s['lat']<BOX[1] and BOX[2]<s['lon']<BOX[3]]
    S+= [{"name":"汉魏洛阳故城*","lat":34.7256,"lon":112.5747},{"name":"偃师商城*","lat":34.7167,"lon":112.7833}]
    RNG=np.random.default_rng(7)
    BG=[(RNG.uniform(BOX[0],BOX[1]),RNG.uniform(BOX[2],BOX[3])) for _ in range(400)]
    out={}
    for R in (6000.0, 20000.0):
        with mp.Pool(3,initializer=init) as p:
            sv=p.map(job,[(s['lat'],s['lon'],R) for s in S])
            bv=p.map(job,[(a,b,R) for a,b in BG])
        sv=np.array(sv,dtype=float); bv=np.array(bv,dtype=float)
        m=np.isfinite(sv); sv2=sv[m]; bv=bv[np.isfinite(bv)]
        th=[np.percentile(bv,q) for q in (95,80)]
        hi=100*float((sv2>=th[1]).mean())
        auc=float(np.mean([(bv<v).mean()+.5*(bv==v).mean() for v in sv2]))
        gain=1-20.0/hi if hi>0 else float('-inf')
        out[int(R)]=dict(auc=auc,site_hi=hi,gain=gain,
                         scores={s['name']:(None if not np.isfinite(v) else float(v)) for s,v in zip(S,sv)})
        print(f"势尺度 {R/1000:.0f} km : AUC={auc:.3f}  古迹落入前20%区的比例={hi:.1f}%  Kvamme增益={gain:+.3f}",flush=True)
    json.dump(out,open('out/scaletest.json','w'),ensure_ascii=False,indent=1,default=float)
    KEY=['二里頭遺址','隋唐洛阳城遗址','东周王城','汉魏洛阳故城*','偃师商城*','邙山陵墓群','白马寺','龙门石窟']
    print(f"\n{'古迹':18s}{'6km':>8s}{'20km':>8s}{'变化':>8s}")
    for k in KEY:
        a=out[6000]['scores'].get(k); b=out[20000]['scores'].get(k)
        if a is None or b is None: continue
        print(f"{k[:16]:18s}{a:8.3f}{b:8.3f}{b-a:+8.3f}")
