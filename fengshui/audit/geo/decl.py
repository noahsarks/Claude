"""同一坐标，三个引擎的地理步骤（磁偏角）分歧有多大。
   NOAA WMM-2025 = fscalc.com 实际调用的数据源（其 app.js: /api/getNoaa → ngdc.noaa.gov）
   Horosa       = 内置 2013-06 城市查表（西偏为正）
   suangua      = 无磁偏角，度数照单全收
"""
import json, subprocess, sys

CITIES = [
    # 名, lat, lon, Horosa 2013 表值（西偏为正）
    ("洛阳",   34.62, 112.45, 4.42),
    ("杭州",   30.27, 120.15, 5.08),
    ("北京",   39.90, 116.41, 6.58),
    ("哈尔滨", 45.80, 126.53, 10.47),
    ("广州",   23.13, 113.26, 2.57),
    ("乌鲁木齐",43.83, 87.62, -2.68),
    ("拉萨",   29.65,  91.14, -0.12),
    ("西安",   34.34, 108.94, 3.48),
]

def noaa(lat, lon, y=2026, m=9, d=2):
    u = ("https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
         f"?lat1={lat}&lon1={lon}&key=zNEw7&resultFormat=json"
         f"&startYear={y}&startMonth={m}&startDay={d}")
    out = subprocess.run(["curl", "-sS", "-m", "60", "-A", "Mozilla/5.0", u],
                         capture_output=True, text=True).stdout
    r = json.loads(out)["result"][0]
    return r["declination"], r["declination_sv"]

print(f"{'城市':<8}{'NOAA东正':>9}{'→西偏':>8}{'Horosa13':>10}{'差':>7}{'占15°山':>9}{'年变率':>8}")
rows = []
for name, la, lo, h13 in CITIES:
    dec_e, sv = noaa(la, lo)
    dec_w = -dec_e                    # 转成 Horosa 的「西偏为正」
    diff = dec_w - h13
    rows.append((name, la, lo, dec_e, dec_w, h13, diff, sv))
    print(f"{name:<8}{dec_e:>9.2f}{dec_w:>8.2f}{h13:>10.2f}{diff:>+7.2f}{abs(diff)/15*100:>8.1f}%{sv:>8.3f}")

print("\n如果有人把 WMM 的东正值直接塞进 Horosa 的西正槽位（该文件自己警告过的坑）：")
for name, la, lo, dec_e, dec_w, h13, diff, sv in rows:
    err = 2 * abs(dec_w)
    print(f"  {name:<8} 符号错 → 偏 {err:5.2f}°  = {err/15:.2f} 个山"
          + ("   ← 跨山" if err > 7.5 else ""))
json.dump([dict(zip("name lat lon noaa_east noaa_west horosa2013 diff sv".split(), r)) for r in rows],
          open('decl.json', 'w'), ensure_ascii=False, indent=1)
