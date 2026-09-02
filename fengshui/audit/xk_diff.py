"""对照：suangua 的挨星顺逆 vs 沈氏玄空标准挨星诀。"""
import sys; sys.path.insert(0, '/home/user/sw/suangua')
from core.fengshui.xuankong import (TWENTY_FOUR_MOUNTAINS as M24, MOUNTAIN_OPPOSITE,
                                    fly_stars, get_mountain_by_name)

GUA_LUOSHU = {"坎":1,"坤":2,"震":3,"巽":4,"乾":6,"兑":7,"艮":8,"离":9}
LUOSHU_GUA = {v:k for k,v in GUA_LUOSHU.items()}

def mountain_of(gua, idx):
    for m in M24:
        if m["gua"] == gua and m["idx"] == idx:
            return m

def polarity_correct(center_star, mtn):
    """标准：入中之星所属卦中、与坐(向)山同序位之山，其阴阳定顺逆。"""
    if center_star == 5:                      # 五无卦，寄本宫（主流约定）
        return mtn["yin_yang"]
    return mountain_of(LUOSHU_GUA[center_star], mtn["idx"])["yin_yang"]

def chart(year_yun, sit_name, correct=True):
    yun = year_yun
    yunp = fly_stars(yun, "yang")
    sit = get_mountain_by_name(sit_name)
    fac = get_mountain_by_name(MOUNTAIN_OPPOSITE[sit_name])
    sl, fl = GUA_LUOSHU[sit["gua"]], GUA_LUOSHU[fac["gua"]]
    cs, cf = yunp[sl], yunp[fl]
    ps = polarity_correct(cs, sit) if correct else sit["yin_yang"]
    pf = polarity_correct(cf, fac) if correct else fac["yin_yang"]
    mc = fly_stars(cs, "yang" if ps == "阳" else "yin")
    fc = fly_stars(cf, "yang" if pf == "阳" else "yin")
    return mc, fc, sl, fl

def verdict(mc, fc, sl, fl, yun):
    ms, mf = mc[sl] == yun, mc[fl] == yun     # 当令山星到坐 / 到向
    fs, ff = fc[sl] == yun, fc[fl] == yun
    if ms and ff: return "旺山旺向"
    if mf and fs: return "上山下水"
    if mf and ff: return "双星到向"
    if ms and fs: return "双星到坐"
    return "其他"

names = [m["name"] for m in M24]
rows, ndiff = [], 0
for yun in range(1, 10):
    for n in names:
        a = verdict(*chart(yun, n, True), yun)
        b = verdict(*chart(yun, n, False), yun)
        if a != b:
            ndiff += 1
            rows.append((yun, n, a, b))
print(f"216 局中，顺逆判定影响格局结论者 {ndiff} 局 ({ndiff/216*100:.0f}%)")
print(f"{'运':>2} {'坐山':>3}  {'标准(沈氏)':<8} {'suangua':<8}")
for r in rows[:40]:
    print(f"{r[0]:>2} {r[1]:>3}  {r[2]:<8} {r[3]:<8}")
print(f"... 共 {ndiff} 条")
# 八运旺山旺向清单核对
std8 = sorted(n for n in names if verdict(*chart(8, n, True), 8) == "旺山旺向")
bad8 = sorted(n for n in names if verdict(*chart(8, n, False), 8) == "旺山旺向")
print("\n八运旺山旺向  标准 :", "、".join(std8))
print("八运旺山旺向 suangua:", "、".join(bad8))
