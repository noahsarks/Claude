# -*- coding: utf-8 -*-
import json, subprocess, time
UA="FengshuiResearch/0.1 (research)"
EPS=["https://overpass-api.de/api/interpreter",
     "https://overpass.kumi.systems/api/interpreter",
     "https://overpass.osm.jp/api/interpreter",
     "https://overpass.private.coffee/api/interpreter"]
def q(query, tries=3):
    for ep in EPS:
        for a in range(tries):
            r=subprocess.run(["curl","-sS","-m","150","-A",UA,"-X","POST","-d",query,ep],
                             capture_output=True,text=True)
            o=r.stdout
            if o.strip().startswith("{"):
                try: return json.loads(o)
                except Exception: pass
            time.sleep(2+2*a)
    return None
