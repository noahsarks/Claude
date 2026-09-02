"""三方对照：沈氏标准 / suangua / Horosa(移植 liqiCore.flyChart)。"""
import sys; sys.path.insert(0, '/home/user/sw/suangua')
sys.path.insert(0, '/home/user/fs/sw')
from xk_diff import chart, verdict, names, M24

# Horosa: SHAN_24 = 山 -> [宫, 元龙, 阴阳(+1阳/-1阴)]
SHAN24 = {
 '壬':(1,'地',1),'子':(1,'天',-1),'癸':(1,'人',-1),
 '未':(2,'地',-1),'坤':(2,'天',1),'申':(2,'人',1),
 '甲':(3,'地',1),'卯':(3,'天',-1),'乙':(3,'人',-1),
 '辰':(4,'地',-1),'巽':(4,'天',1),'巳':(4,'人',1),
 '丙':(9,'地',1),'午':(9,'天',-1),'丁':(9,'人',-1),
 '庚':(7,'地',1),'酉':(7,'天',-1),'辛':(7,'人',-1),
 '戌':(6,'地',-1),'乾':(6,'天',1),'亥':(6,'人',1),
 '丑':(8,'地',-1),'艮':(8,'天',1),'寅':(8,'人',1)}
OPP_GONG = {1:9,9:1,2:8,8:2,3:7,7:3,4:6,6:4}
GONG_YUAN = {f"{g}|{y}": (s, yy) for s,(g,y,yy) in SHAN24.items()}

def _idx(n): return (n-5+9)%9
def _val(c,n,fwd): return ((c-1+_idx(n))%9+1) if fwd else (((c-1-_idx(n))%9+9)%9+1)

def horosa(yun, xiang):          # 入参是「向首山」
    gX,yX,yyX = SHAN24[xiang]
    gZ = OPP_GONG[gX]; zuo = GONG_YUAN[f"{gZ}|{yX}"][0]
    yunp = {n:_val(yun,n,True) for n in range(1,10)}
    Vx = yunp[gX]; fx = (yyX==1) if Vx==5 else (GONG_YUAN[f"{Vx}|{yX}"][1]==1)
    xp = {n:_val(Vx,n,fx) for n in range(1,10)}
    Vs = yunp[gZ]; yyZ = SHAN24[zuo][2]
    fs = (yyZ==1) if Vs==5 else (GONG_YUAN[f"{Vs}|{yX}"][1]==1)
    sp = {n:_val(Vs,n,fs) for n in range(1,10)}
    return zuo, sp, xp, gZ, gX

OPP = {m["name"]: None for m in M24}
from core.fengshui.xuankong import MOUNTAIN_OPPOSITE

agree_h, agree_s, tot = 0, 0, 0
mis = []
for yun in range(1,10):
    for sit in names:
        std = verdict(*chart(yun, sit, True), yun)
        sg  = verdict(*chart(yun, sit, False), yun)
        zuo, sp, xp, gZ, gX = horosa(yun, MOUNTAIN_OPPOSITE[sit])
        assert zuo == sit, (yun, sit, zuo)
        hr = verdict(sp, xp, gZ, gX, yun)
        tot += 1
        agree_h += (hr == std); agree_s += (sg == std)
        if hr != std: mis.append((yun, sit, std, hr))
print(f"共 {tot} 局（9 运 × 24 坐山）")
print(f"Horosa  与沈氏标准一致：{agree_h}/{tot} = {agree_h/tot*100:.1f}%")
print(f"suangua 与沈氏标准一致：{agree_s}/{tot} = {agree_s/tot*100:.1f}%")
if mis: print("Horosa 不一致者：", mis[:10])
# 抽查：八运四大格局清单
for tag, fn in (("标准", lambda n: verdict(*chart(8,n,True),8)),
                ("Horosa", lambda n: verdict(*horosa(8, MOUNTAIN_OPPOSITE[n]), 8)),
                ("suangua", lambda n: verdict(*chart(8,n,False),8))):
    d = {}
    for n in names: d.setdefault(fn(n), []).append(n)
    print(f"\n八运·{tag}")
    for k in ("旺山旺向","上山下水","双星到向","双星到坐"):
        print(f"  {k}: {'、'.join(d.get(k,[])) or '—'}")
