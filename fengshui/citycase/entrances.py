import json, subprocess
Q="""[out:json][timeout:60];
(node["entrance"](31.234,121.499,31.239,121.505);
 node["entrance"](25.032,121.562,25.036,121.567););
out body;"""
o=subprocess.run(["curl","-sS","-m","90","-A","FengshuiResearch/0.1","-X","POST","-d",Q,
  "https://overpass.kumi.systems/api/interpreter"],capture_output=True,text=True).stdout
d=json.loads(o)
print("entrance nodes:", len(d.get("elements",[])))
for e in d.get("elements",[])[:25]:
    t=e.get("tags",{})
    print(f"  {e['lat']:.5f},{e['lon']:.5f}  {t.get('entrance')}  {t.get('name','')}")
json.dump(d.get("elements",[]), open('entrances.json','w'), ensure_ascii=False)
