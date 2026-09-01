"""对洛阳分级图做 Kvamme 分析并出图。"""
import json, math, numpy as np, base64, io
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

G=np.load('out/luoyang_grid.npy'); M=json.load(open('out/luoyang_meta.json'))
lats=np.array(M['lats']); lons=np.array(M['lons'])
ok=np.isfinite(G)
# 五级：按本图自身分位切，%面积由构造精确已知
QS=[95,80,55,25]; TH=[np.nanpercentile(G,q) for q in QS]
def grade(v):
    if not np.isfinite(v): return 0
    for i,t in enumerate(TH):
        if v>=t: return i+1
    return 5
Gr=np.vectorize(grade)(G)
AREA=[float((Gr==i).sum())/ok.sum()*100 for i in range(1,6)]

SITES=json.load(open('guobao.json'))
B=M['box']
S=[s for s in SITES if B[0]<s['lat']<B[1] and B[2]<s['lon']<B[3]]
EXTRA=[{"name":"汉魏洛阳故城*","lat":34.7256,"lon":112.5747},
       {"name":"偃师商城*","lat":34.7167,"lon":112.7833}]
S=S+[e for e in EXTRA if B[0]<e['lat']<B[1] and B[2]<e['lon']<B[3]]
def at(la,lo):
    i=int(np.argmin(np.abs(lats-la))); j=int(np.argmin(np.abs(lons-lo)))
    return int(Gr[i,j]), float(G[i,j])
rows=[]
for s in S:
    g,v=at(s['lat'],s['lon'])
    rows.append(dict(name=s['name'],lat=s['lat'],lon=s['lon'],grade=g,score=v))
rows.sort(key=lambda r:(r['grade'],-r['score']))
n=len([r for r in rows if r['grade']>0])
def kv(a,p): return 1-a/p if p>0 else float('-inf')
cum_area=AREA[0]+AREA[1]; cum_site=100*len([r for r in rows if 0<r['grade']<=2])/n
g1_site=100*len([r for r in rows if r['grade']==1])/n
print(f"格点 {ok.sum()}，古迹 {n} 处")
print(f"\n{'级':>3s}{'占面积%':>9s}{'占古迹%':>9s}{'增益':>8s}")
for i in range(5):
    ps=100*len([r for r in rows if r['grade']==i+1])/n
    print(f"{['I','II','III','IV','V'][i]:>3s}{AREA[i]:9.1f}{ps:9.1f}{kv(AREA[i],ps):8.3f}")
print(f"\nI+II 合计: 面积 {cum_area:.1f}%  古迹 {cum_site:.1f}%  Kvamme 增益 = {kv(cum_area,cum_site):.3f}")
print(f"仅 I 级:   面积 {AREA[0]:.1f}%  古迹 {g1_site:.1f}%  增益 = {kv(AREA[0],g1_site):.3f}")
# 二项检验：古迹落入 I+II 是否显著多于按面积期望
from scipy import stats
k=len([r for r in rows if 0<r['grade']<=2])
p=stats.binomtest(k,n,cum_area/100,alternative='greater').pvalue
print(f"二项检验 p = {p:.4f}  ({k}/{n} 落入 I+II，期望 {cum_area/100*n:.1f})")

print(f"\n{'古迹':22s}{'级':>3s}{'分':>7s}")
for r in rows: print(f"{r['name'][:20]:22s}{['—','I','II','III','IV','V'][r['grade']]:>3s}{r['score']:7.3f}")

# 出图
cmap=ListedColormap(['#1c574c','#40765d','#6c7740','#8e653a','#7c4a36'])
fig,ax=plt.subplots(figsize=(11,6.4),dpi=170)
im=ax.imshow(np.where(Gr>0,Gr,np.nan),cmap=cmap,vmin=.5,vmax=5.5,
             extent=[lons[0],lons[-1],lats[-1],lats[0]],aspect='auto',interpolation='nearest')
for r in rows:
    ax.plot(r['lon'],r['lat'],'o',ms=5,mfc='white',mec='#111',mew=1.1,zorder=3)
KEY=['二里頭遺址','隋唐洛阳城遗址','东周王城','邙山陵墓群','白马寺','龙门石窟','汉魏洛阳故城*','偃师商城*','恭陵','洛南东汉帝陵']
for r in rows:
    if r['name'] in KEY:
        ax.annotate(r['name'].replace('*',''),(r['lon'],r['lat']),textcoords='offset points',
                    xytext=(6,4),fontsize=6.5,color='white',
                    path_effects=None,zorder=4,
                    bbox=dict(boxstyle='round,pad=0.18',fc='#111',ec='none',alpha=.62))
cb=fig.colorbar(im,ax=ax,ticks=[1,2,3,4,5],pad=.015,fraction=.032)
cb.ax.set_yticklabels(['I 极优','II 优良','III 中平','IV 平常','V 欠佳'],fontsize=8)
ax.set_xlabel('经度 E',fontsize=8); ax.set_ylabel('纬度 N',fontsize=8)
ax.tick_params(labelsize=7)
plt.rcParams['font.sans-serif']=['Noto Sans CJK SC','DejaVu Sans']
fig.tight_layout()
fig.savefig('out/luoyang_map.png',bbox_inches='tight')
print("\n图已保存 out/luoyang_map.png")
json.dump(dict(area=AREA,rows=rows,gain_I=kv(AREA[0],g1_site),
               gain_I_II=kv(cum_area,cum_site),binom_p=float(p),n=n,
               thresholds=[float(t) for t in TH]),
          open('out/luoyang_report.json','w'),ensure_ascii=False,indent=1,default=float)
