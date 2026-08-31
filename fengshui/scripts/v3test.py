"""用已存的晋南豫北样本，比较 v0.2 与 v0.3 在建筑类(聚落型)上的判别力。"""
import sys, json, numpy as np
sys.path.insert(0,'/home/user/fs'); import luantou as V3, kvamme as K
reg=K.Mosaic('晋南豫北',range(34,37),range(112,115))
BG=json.load(open('out/bg_晋南豫北.json'))[:1200]
POS=json.load(open('out/pos_晋南豫北.json'))
def sc(la,lo):
    s=V3.score(V3.metrics(reg,la,lo)); return s['final'] if s else None
bg3=np.array([v for v in (sc(b['lat'],b['lon']) for b in BG) if v is not None])
print('背景重算完成',len(bg3),flush=True)
out={}
for kind in ('tomb','building'):
    P=[p for p in POS if p['k']==kind]
    old=np.array([p['score'] for p in P])
    bgo=np.array([b['score'] for b in BG])
    new=np.array([v for v in (sc(p['lat'],p['lon']) for p in P) if v is not None])
    a_old=float(np.mean([(bgo<v).mean()+.5*(bgo==v).mean() for v in old]))
    a_new=float(np.mean([(bg3<v).mean()+.5*(bg3==v).mean() for v in new]))
    out[kind]=dict(n=len(P),auc_v2=a_old,auc_v3=a_new)
    print(f"{kind:9s} n={len(P):4d}  AUC v0.2={a_old:.3f}  →  v0.3={a_new:.3f}  ({a_new-a_old:+.3f})",flush=True)
json.dump(out,open('out/v3test.json','w'),indent=1,default=float)
