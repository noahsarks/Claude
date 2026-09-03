# -*- coding: utf-8 -*-
"""明堂扇区半角的敏感性扫描。
   ±45° 这个数字《葬经翼》里没有——原文只说「穴前」。既然是我定的，
   就得知道结论对它有多敏感：半角从 20° 扫到 90°，看每点的水类在哪里翻。"""
import sys, os, yaml, importlib, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')); import kvamme as K
def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m
HERE = os.path.dirname(os.path.abspath(__file__))
V = load(os.path.join(os.path.dirname(HERE), 'luantou.py'), 'lt')
S = yaml.safe_load(open(os.path.join(HERE, 'sites.yaml'), encoding='utf8'))['sites']
HALF = [20, 30, 40, 45, 50, 60, 75, 90]
src = open(os.path.join(os.path.dirname(HERE), 'luantou.py'), encoding='utf8').read()
print(f"{'点':<18}" + ''.join(f"{h:>7}" for h in HALF))
for s in S:
    if s['坐'] is None:
        print(f"{s['name']:<18}坐向无据，不判"); continue
    reg = K.Mosaic('x', range(int(s['lat']), int(s['lat'])+1), range(int(s['lon']), int(s['lon'])+1))
    h0 = float(np.atleast_1d(reg.sample(np.array([s['lat']]), np.array([s['lon']])))[0])
    row = []
    for hw in HALF:
        g = dict(V.__dict__)
        exec(src.replace('<= 45) & (d > 80 * S)', f'<= {hw}) & (d > 80 * S)'), g)
        r = g['_mingtang_water'](reg, s['lat'], s['lon'], h0, float(s['坐']), 1.0, True)
        row.append(r['mt_class'])
    print(f"{s['name']:<18}" + ''.join(f"{c:>7}" for c in row))
