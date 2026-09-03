# -*- coding: utf-8 -*-
"""从已知一篇沿「前一篇」向前走，收集《沈氏玄空学》连载。
   沈竹礽 1849-1906、王则先 民国 —— 原文与则先按语为公有领域。"""
import re, html, json, os, subprocess, time
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
os.makedirs('/home/user/ms/shen', exist_ok=True)

def get(url):
    for a in range(3):
        r = subprocess.run(["curl","-sSL","-m","45","-A",UA,url], capture_output=True)
        t = r.stdout.decode('utf8','replace')
        if len(t) > 8000: return t
        time.sleep(2)
    return ''

def title_of(h):
    m = re.search(r'<title>([^<]+)</title>', h)
    return html.unescape(m.group(1)).strip() if m else ''

def prev_of(h):
    m = re.search(r'前一篇[^<]*<a[^>]*href="([^"]+)"', h) or \
        re.search(r'id="fanye_prev"[^>]*>\s*<a[^>]*href="([^"]+)"', h)
    if m: return m.group(1)
    ls = re.findall(r'href="(//blog\.sina\.com\.cn/s/blog_537afff0[0-9a-z]+\.html)"', h)
    return ls[0] if ls else None

def body(h):
    m = re.search(r'(?s)<div[^>]*class="articalContent[^"]*"[^>]*>(.*?)</div>', h)
    t = m.group(1) if m else h
    t = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', t)
    t = re.sub(r'(?i)<(br|/p|/div)\s*/?>', '\n', t)
    return '\n'.join(l.strip() for l in html.unescape(re.sub(r'<[^>]+>','',t)).split('\n') if l.strip())

url = 'http://blog.sina.com.cn/s/blog_537afff00102y37n.html'
found, steps = {}, 0
while url and steps < 900:
    h = get(url)
    if not h: break
    ti = title_of(h)
    if '沈氏玄空学' in ti or '沈氏玄空學' in ti:
        key = re.search(r'blog_(537afff0[0-9a-z]+)', url).group(1)
        open(f'/home/user/ms/shen/{key}.txt','w',encoding='utf8').write(ti+'\n\n'+body(h))
        found[key] = ti
        print(len(found), ti, flush=True)
    p = prev_of(h)
    url = ('http:'+p) if p and p.startswith('//') else p
    steps += 1
json.dump(found, open('/home/user/ms/shen_found.json','w'), ensure_ascii=False, indent=1)
print('走了', steps, '步，收到', len(found), '篇')
