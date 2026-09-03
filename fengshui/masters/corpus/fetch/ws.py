# -*- coding: utf-8 -*-
import json, time, urllib.parse, subprocess, sys
UA = "FengshuiResearchBot/0.1 (research; contact via github.com/noahsarks/Claude)"
def api(params, host="zh.wikisource.org"):
    u = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    for a in range(5):
        r = subprocess.run(["curl","-sS","-m","60","-A",UA,u], capture_output=True, text=True)
        t = r.stdout
        if t.startswith("{"):
            return json.loads(t)
        time.sleep(4 * (a + 1))
    return None
def search(q, host="zh.wikisource.org", ns=0, n=8):
    d = api({"action":"query","list":"search","srsearch":q,"srlimit":n,
             "srnamespace":ns,"format":"json"}, host)
    if not d: return None
    s = d["query"]
    return s["searchinfo"]["totalhits"], [x["title"] for x in s["search"]]
if __name__ == "__main__":
    for q in sys.argv[1:]:
        r = search(q)
        print(f"=== {q} ===")
        if r is None: print("  失败")
        else:
            print("  hits", r[0])
            for t in r[1]: print("   -", t)
        time.sleep(3)

def page(title, host="zh.wikisource.org"):
    d = api({"action":"parse","page":title,"prop":"wikitext","format":"json",
             "formatversion":"2"}, host)
    if not d or "parse" not in d: return None
    return d["parse"]["wikitext"]

def links(title, host="zh.wikisource.org", n=500):
    d = api({"action":"parse","page":title,"prop":"links","format":"json",
             "formatversion":"2"}, host)
    if not d or "parse" not in d: return []
    return [l["title"] for l in d["parse"].get("links",[])]

def plaintext(title, host="zh.wikisource.org"):
    d = api({"action":"query","prop":"extracts","titles":title,
             "explaintext":"1","format":"json","formatversion":"2"}, host)
    if not d: return None
    pg = d["query"]["pages"][0]
    return pg.get("extract")
