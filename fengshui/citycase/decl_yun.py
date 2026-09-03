# -*- coding: utf-8 -*-
import json, subprocess
def noaa(lat, lon, y, m=6, d=15):
    u=("https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
       f"?lat1={lat}&lon1={lon}&key=zNEw7&resultFormat=json&model=IGRF&startYear={y}&startMonth={m}&startDay={d}")
    o=subprocess.run(["curl","-sS","-m","60","-A","Mozilla/5.0",u],capture_output=True,text=True).stdout
    r=json.loads(o)["result"][0]; return r["declination"], json.loads(o)["model"]
G=json.load(open('geom.json'))
# 建成/入伙年 —— 决定元运（本盘定终身不变）
YEAR={'金茂大厦':1999,'上海环球金融中心':2008,'上海中心大厦':2016,'东方明珠电视塔':1994,'台北101':2004}
YUN=[(1,1864,1883),(2,1884,1903),(3,1904,1923),(4,1924,1943),(5,1944,1963),
     (6,1964,1983),(7,1984,2003),(8,2004,2023),(9,2024,2043)]
def yun_of(y):
    for k,a,b in YUN:
        if a<=y<=b: return k
out={}
print(f"{'建筑':<16}{'年':>6}{'元运':>4}  {'磁偏角(建成年)':>14}{'磁偏角(2026)':>13}  模型")
for n,g in G.items():
    y=YEAR.get(n)
    if not y: continue
    d0,m0=noaa(g['lat'],g['lon'],y); d1,m1=noaa(g['lat'],g['lon'],2026)
    out[n]=dict(**g, year=y, yun=yun_of(y), decl_build=d0, decl_2026=d1, model=m1)
    print(f"{n:<16}{y:>6}{yun_of(y):>4}  {d0:>13.2f}°{d1:>12.2f}°  {m1}")
json.dump(out, open('city.json','w'), ensure_ascii=False, indent=1)
