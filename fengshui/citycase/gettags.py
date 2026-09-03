import sys, json; sys.path.insert(0,'/home/user/city')
from op import q
Q='''[out:json][timeout:90];
(way["name"~"上海中心|金茂大厦|环球金融中心"](31.22,121.49,31.25,121.52);
 way["name"~"台北101|Taipei 101"](25.02,121.55,25.05,121.58););
out tags;'''
d=q(Q)
print('ok' if d else 'FAILED')
if d:
    json.dump(d, open('/home/user/city/tags.json','w'), ensure_ascii=False)
    for e in d.get('elements',[]):
        t=e.get('tags',{})
        print('---', t.get('name'), ' id', e['id'])
        for k,v in sorted(t.items()):
            if k.startswith('name'): continue
            print(f'    {k} = {v}')
