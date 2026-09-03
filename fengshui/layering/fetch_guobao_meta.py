# -*- coding: utf-8 -*-
"""从维基百科「第N批全国重点文物保护单位」名录取 类别 与 时代。
   编号形如 1-0001-5-001，第三段是官方类别码：
     1古遗址 2古墓葬 3古建筑 4石窟寺及石刻 5近现代重要史迹及代表性建筑 6其他
   这比 Wikidata 的 P31（73% 是「文物保护单位」这种无用值）好得多，且「时代」列覆盖近全。"""
import sys, re, json, time
sys.path.insert(0, '/home/user/ms')
from ws import api

CAT = {'1':'古遗址','2':'古墓葬','3':'古建筑','4':'石窟寺及石刻',
       '5':'近现代重要史迹及代表性建筑','6':'其他'}
CN = ['一','二','三','四','五','六','七','八']
rows = {}
for i, c in enumerate(CN, 1):
    d = api({'action':'parse','page':f'第{c}批全国重点文物保护单位',
             'prop':'wikitext','format':'json','formatversion':'2'}, host='zh.wikipedia.org')
    if not d or 'parse' not in d:
        print(f'第{c}批 取不到'); continue
    w = d['parse']['wikitext']
    n0 = len(rows)
    # 行形如： | 1 || 1-0001-5-001 || [[名称]] |图片|| 时代 || 地址
    for m in re.finditer(r'\|\s*\d+\s*\|\|\s*(\d)-(\d+)-(\d)-(\d+)\s*\|\|\s*(.+?)(?=\n\|-|\n\|\}|\Z)',
                         w, re.S):
        cat = m.group(3); body = m.group(5)
        cells = [x.strip() for x in re.split(r'\|\||\n\|', body)]
        name = re.sub(r'^\[\[|\]\]$', '', cells[0]) if cells else ''
        name = name.split('|')[-1].strip()
        era = ''
        for cell in cells[1:]:
            if cell.startswith('[[File:') or cell.startswith('[[image:'): continue
            if re.search(r'(年|世纪|前|新石器|旧石器|商|周|秦|汉|晋|唐|宋|辽|金|元|明|清|民国|春秋|战国|三国|南北朝|隋|五代|西夏|吐蕃)', cell):
                era = cell.split('||')[0].strip(); break
        if name:
            rows[name] = dict(batch=i, cat_code=cat, cat=CAT.get(cat,'?'), era=era)
    print(f'第{c}批 +{len(rows)-n0}  累计 {len(rows)}', flush=True)
    time.sleep(2)
json.dump(rows, open('/home/user/fs/guobao_meta.json','w'), ensure_ascii=False)
import collections
print('\n类别分布:', dict(collections.Counter(v['cat'] for v in rows.values())))
print('有时代:', sum(1 for v in rows.values() if v['era']), '/', len(rows))
