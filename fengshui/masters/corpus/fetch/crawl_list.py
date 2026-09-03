# -*- coding: utf-8 -*-
"""抓 sina 博客「山水清澈」全部博文目录（191 页），筛出《沈氏玄空学》连载。"""
import re, html, json, os, time, subprocess
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
UIDN = 1400569840
os.makedirs('/home/user/ms/al', exist_ok=True)
seen = {}
def grab(p):
    f = f'/home/user/ms/al/f{p}.html'
    if os.path.exists(f) and os.path.getsize(f) > 30000:
        return open(f, encoding='utf8', errors='replace').read()
    for a in range(4):
        r = subprocess.run(["curl","-sSL","-m","45","-A",UA,
            f"http://blog.sina.com.cn/s/articlelist_{UIDN}_0_{p}.html"],
            capture_output=True)
        t = r.stdout.decode('utf8','replace')
        if len(t) > 30000:
            open(f,'w',encoding='utf8').write(t); return t
        time.sleep(2+a*2)
    return ''
for p in range(1, 192):
    h = grab(p)
    n0 = len(seen)
    for m in re.finditer(r'href="(//blog\.sina\.com\.cn/s/blog_537afff0[0-9a-z]+\.html)"[^>]*>\s*([^<]{1,90})\s*</a>', h):
        seen['http:'+m.group(1)] = html.unescape(m.group(2)).strip()
    if p % 20 == 0 or p == 191:
        print(p, '累计', len(seen), flush=True)
json.dump(seen, open('/home/user/ms/sina_all.json','w'), ensure_ascii=False, indent=1)
shen = {u:t for u,t in seen.items() if '沈氏玄空学' in t or '沈氏玄空學' in t}
json.dump(shen, open('/home/user/ms/shen_index.json','w'), ensure_ascii=False, indent=1)
print('总文章', len(seen), '沈氏玄空学', len(shen))
