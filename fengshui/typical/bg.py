# -*- coding: utf-8 -*-
"""本地背景分位：把单点分数放回它自己的周边分布里读。
   同瓦片内以站点为心、半径 15 km 内均匀取 400 点，坐向沿用该站点的坐向
   （坐向未知者不判水项，两边一致），剔除非有限值后计算经验分位。"""
import sys, os, math, yaml, importlib, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import kvamme as K
HERE = os.path.dirname(os.path.abspath(__file__))
S = yaml.safe_load(open(os.path.join(HERE, 'sites.yaml'), encoding='utf8'))['sites']

def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(sp); sys.modules[n] = m
    sp.loader.exec_module(m); return m
V7 = load(os.path.join(os.path.dirname(HERE), 'luantou.py'), 'lt_v7')

regs = {}
def region(lat, lon):
    k = (int(lat), int(lon))
    if k not in regs:
        regs[k] = K.Mosaic(f'{k}', range(k[0], k[0]+1), range(k[1], k[1]+1))
    return regs[k]

print(f"{'点':<18}{'得分':>7}{'背景均':>8}{'SD':>7}{'n':>5}{'分位':>7}")
rng = np.random.default_rng(11)
out = {}
for s in S:
    reg = region(s['lat'], s['lon']); th = s['坐']
    try:
        r7 = V7.score(V7.metrics(reg, s['lat'], s['lon'], theta_deg=th))['final']
    except Exception as e:
        print(f"{s['name']:<18}站点计算失败 {e}"); continue
    vals = []
    for _ in range(400):
        a = rng.uniform(0, 2*math.pi); rr = 15000*math.sqrt(rng.uniform())
        dla = rr*math.cos(a)/110540
        dlo = rr*math.sin(a)/(111320*math.cos(math.radians(s['lat'])))
        try:
            mm = V7.metrics(reg, s['lat']+dla, s['lon']+dlo, theta_deg=th)
            if not mm: continue
            v = V7.score(mm)['final']
            if v is not None and np.isfinite(v): vals.append(float(v))
        except Exception: pass
    if len(vals) < 50:
        print(f"{s['name']:<18}{r7:7.3f}   背景有效点仅 {len(vals)}，不判"); continue
    v = np.array(vals); q = float((v < r7).mean())
    out[s['name']] = dict(score=round(r7,3), mean=round(float(v.mean()),3),
                          sd=round(float(v.std()),3), n=len(vals), pct=round(q*100))
    print(f"{s['name']:<18}{r7:7.3f}{v.mean():8.3f}{v.std():7.3f}{len(vals):5d}{q*100:6.0f}%")
yaml.safe_dump(out, open(os.path.join(HERE,'bg.yaml'),'w',encoding='utf8'),
               allow_unicode=True, sort_keys=False)
