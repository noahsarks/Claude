# -*- coding: utf-8 -*-
"""抓页面 → 提取正文纯文本。存 raw/ 与 txt/。"""
import sys, os, re, html, subprocess, hashlib
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
os.makedirs('/home/user/ms/raw', exist_ok=True)
os.makedirs('/home/user/ms/txt', exist_ok=True)

def clean(h):
    h = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', h)
    h = re.sub(r'(?is)<!--.*?-->', ' ', h)
    h = re.sub(r'(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>', '\n', h)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = html.unescape(h)
    h = re.sub(r'[ \t\xa0]+', ' ', h)
    h = re.sub(r'\n\s*\n\s*\n+', '\n\n', h)
    return '\n'.join(l.strip() for l in h.split('\n') if l.strip())

def get(url, name=None, referer=None):
    name = name or hashlib.md5(url.encode()).hexdigest()[:10]
    cmd = ["curl", "-sSL", "-m", "60", "-A", UA]
    if referer: cmd += ["-H", f"Referer: {referer}"]
    cmd += [url]
    r = subprocess.run(cmd, capture_output=True)
    raw = r.stdout
    for enc in ('utf-8', 'gb18030', 'big5'):
        try:
            t = raw.decode(enc); break
        except Exception: continue
    else:
        t = raw.decode('utf-8', 'replace')
    open(f'/home/user/ms/raw/{name}.html', 'w', encoding='utf8').write(t)
    c = clean(t)
    open(f'/home/user/ms/txt/{name}.txt', 'w', encoding='utf8').write(c)
    return name, len(c)

if __name__ == '__main__':
    for a in sys.argv[1:]:
        u, _, n = a.partition('##')
        print(*get(u, n or None))
