# -*- coding: utf-8 -*-
"""从 OpenStreetMap 取目标建筑的实测轮廓（ODbL）。"""
import json, subprocess, time, sys
UA = "FengshuiResearch/0.1 (research)"
EP = "https://overpass-api.de/api/interpreter"

Q = """
[out:json][timeout:90];
(
  way["name"~"上海中心|Shanghai Tower"](31.22,121.49,31.25,121.52);
  way["name"~"环球金融中心|World Financial Cent"](31.22,121.49,31.25,121.52);
  way["name"~"金茂大厦|Jin Mao"](31.22,121.49,31.25,121.52);
  way["name"~"东方明珠|Oriental Pearl"](31.22,121.49,31.25,121.52);
  way["name"~"台北101|Taipei 101|臺北101"](25.02,121.55,25.05,121.58);
);
out geom tags;
"""
r = subprocess.run(["curl","-sS","-m","120","-A",UA,"-X","POST","-d",Q,EP],
                   capture_output=True, text=True)
d = json.loads(r.stdout)
print("elements:", len(d.get("elements", [])))
out = []
for e in d["elements"]:
    t = e.get("tags", {})
    g = e.get("geometry") or []
    if not g: continue
    out.append(dict(id=e["id"], name=t.get("name"), name_en=t.get("name:en"),
                    height=t.get("height"), levels=t.get("building:levels"),
                    start=t.get("start_date"), building=t.get("building"),
                    geom=[(p["lat"], p["lon"]) for p in g]))
    print(f"  {t.get('name','?'):<28} h={t.get('height','?'):<7} lv={t.get('building:levels','?'):<5} pts={len(g)}")
json.dump(out, open('/home/user/city/osm_buildings.json','w'), ensure_ascii=False)
