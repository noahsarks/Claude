# -*- coding: utf-8 -*-
"""下载《欽定古今圖書集成·博物彙編·藝術典·堪輿部》全部卷（第651-680卷）。
   公有领域（作者逝世逾百年，1931 前出版）。来源 zh.wikisource.org"""
import sys, re, html, time, os
sys.path.insert(0, '/home/user/ms')
from ws import api
os.makedirs('/home/user/ms/gjtsjc', exist_ok=True)

def txt(title):
    d = api({'action':'parse','page':title,'prop':'text','format':'json','formatversion':'2'})
    if not d or 'parse' not in d: return None
    t = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', d['parse']['text'])
    t = re.sub(r'(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    return '\n'.join(l.strip() for l in t.split('\n') if l.strip())

ok = 0
for v in range(651, 681):
    p = f'/home/user/ms/gjtsjc/{v}.txt'
    if os.path.exists(p) and os.path.getsize(p) > 2000:
        print(v, 'skip'); continue
    t = txt(f'欽定古今圖書集成/博物彙編/藝術典/第{v}卷')
    if t and len(t) > 500:
        open(p, 'w', encoding='utf8').write(t); ok += 1
        print(v, len(t))
    else:
        print(v, 'EMPTY')
    time.sleep(2)
print('done, 新增', ok)
