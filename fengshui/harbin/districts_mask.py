# -*- coding: utf-8 -*-
"""把 OSM 关系成员（一段段边界线）拼成闭合环，再做点在多边形内的判定。

必要性：用户说的「市区」是六个市辖区，不是我画的矩形框。
用行政边界裁，一是不把阿城、玉泉这类不属于市区的地方算进来，
二是不把道外、松北的远郊截掉半截。
"""
import os, json
import numpy as np
from matplotlib.path import Path
HERE = os.path.dirname(os.path.abspath(__file__))

def _key(p, q=6):
    return (round(p[0], q), round(p[1], q))

def assemble(rings):
    """按端点相接把线段链成闭合环。OSM 的 relation 成员是无序的 way。"""
    segs = [list(map(tuple, r)) for r in rings if len(r) >= 2]
    out, used = [], [False] * len(segs)
    for i in range(len(segs)):
        if used[i]: continue
        used[i] = True
        cur = list(segs[i])
        grew = True
        while grew:
            grew = False
            for j in range(len(segs)):
                if used[j]: continue
                s = segs[j]
                if _key(s[0]) == _key(cur[-1]):
                    cur += s[1:]; used[j] = True; grew = True
                elif _key(s[-1]) == _key(cur[-1]):
                    cur += s[::-1][1:]; used[j] = True; grew = True
                elif _key(s[-1]) == _key(cur[0]):
                    cur = s[:-1] + cur; used[j] = True; grew = True
                elif _key(s[0]) == _key(cur[0]):
                    cur = s[::-1][:-1] + cur; used[j] = True; grew = True
            if _key(cur[0]) == _key(cur[-1]) and len(cur) > 3:
                break
        if len(cur) >= 4:
            out.append(cur)
    return out

class Districts:
    def __init__(self, path=None):
        path = path or os.path.join(HERE, 'districts.json')
        self.raw = json.load(open(path, encoding='utf8'))
        self.paths = {}
        for d in self.raw:
            rings = assemble(d['rings'])
            # 只留够大的环，丢掉没闭合的碎片
            self.paths[d['name']] = [Path(np.array([[p[1], p[0]] for p in r]))
                                     for r in rings if len(r) >= 20]
    def which(self, lat, lon):
        for nm, ps in self.paths.items():
            for p in ps:
                if p.contains_point((lon, lat)):
                    return nm
        return None
    def contains(self, lat, lon):
        return self.which(lat, lon) is not None
    def bbox(self):
        la = [p[0] for d in self.raw for r in d['rings'] for p in r]
        lo = [p[1] for d in self.raw for r in d['rings'] for p in r]
        return min(la), max(la), min(lo), max(lo)

if __name__ == '__main__':
    D = Districts()
    print('装配结果：')
    for nm, ps in D.paths.items():
        print(f'  {nm:<6} {len(ps)} 个闭环，共 {sum(len(p.vertices) for p in ps)} 点')
    print('外接框 lat %.3f–%.3f  lon %.3f–%.3f' % D.bbox())
    for la, lo, nm in [(45.7565,126.6424,'索菲亚教堂'),(45.5957,126.6311,'平房区政府'),
                       (45.7930,126.5086,'松北区政府'),(45.5362,126.9694,'阿城（应在区外）'),
                       (45.4145,127.1574,'玉泉（应在区外）'),(45.9734,126.6014,'呼兰（应在区外）')]:
        print(f'  {nm:<16} → {D.which(la, lo)}')
