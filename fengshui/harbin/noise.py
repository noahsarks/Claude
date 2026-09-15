# -*- coding: utf-8 -*-
"""位移噪声底：把穴位挪 250/500/1000 m，分数会变多少？

为什么在市区尺度必须先做这个：哈尔滨市区是一块平地，3 km 起伏中位只有几十米。
如果「挪 500 m 引起的分数变化」和「全城分数的空间差异」同量级，
那张图上的高低就是噪声，不能读。
本项目在晋南豫北做过同类测量（1 km 位移噪声 0.042 ≈ 效应量 0.043，信噪比 1:1）。
"""
import os, sys, math, json, importlib.util
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'scripts'))

def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m
L = load(os.path.join(REPO, 'luantou.py'), 'luantou'); sys.modules['luantou'] = L
import kvamme as K
G = load(os.path.join(HERE, 'grid.py'), 'hgrid')

N_SITE, N_OFF = 40, 8
RADII = [250.0, 500.0, 1000.0]

if __name__ == '__main__':
    scope = sys.argv[1] if len(sys.argv) > 1 else 'city'
    d = json.load(open(os.path.join(HERE, f'grid_{scope}.json'), encoding='utf8'))
    rows = [r for r in d['rows'] if r]
    Mall = np.array([r['modern'] for r in rows]); Zall = np.array([r['zjy'] for r in rows])
    reg = K.Mosaic('harbin', range(45, 47), range(125, 128))
    ways = json.load(open(os.path.join(HERE, 'osm_rivers_harbin.json'), encoding='utf8'))
    L.attach_external_rivers(reg, ways)
    rng = np.random.default_rng(7)
    pick = rng.choice(len(rows), N_SITE, replace=False)
    print(f'范围 {scope}：全域分数空间 SD —— 现代版 {Mall.std():.4f}，葬經翼 {Zall.std():.4f}\n')
    print(f"{'位移半径':>8}{'现代版 SD':>12}{'信噪比':>8}{'葬經翼 SD':>12}{'信噪比':>8}")
    out = {}
    for R in RADII:
        sm, sz = [], []
        for i in pick:
            r0 = rows[i]
            vm, vz = [], []
            for k in range(N_OFF):
                a = 2 * math.pi * k / N_OFF
                la = r0['lat'] + R * math.cos(a) / 110540.0
                lo = r0['lon'] + R * math.sin(a) / (111320.0 * math.cos(math.radians(r0['lat'])))
                try:
                    M = L.metrics(reg, la, lo, theta_deg=0.0)
                except Exception:
                    M = None
                if M is None: continue
                vm.append(G.score_modern(M)['final']); vz.append(G.score_zangjingyi(M)['final'])
            if len(vm) >= 5:
                sm.append(np.std(vm)); sz.append(np.std(vz))
        m_, z_ = float(np.mean(sm)), float(np.mean(sz))
        out[R] = dict(modern_sd=round(m_, 4), zjy_sd=round(z_, 4),
                      modern_snr=round(Mall.std() / m_, 2), zjy_snr=round(Zall.std() / z_, 2))
        print(f"{R:8.0f}{m_:12.4f}{Mall.std()/m_:8.2f}{z_:12.4f}{Zall.std()/z_:8.2f}")
    out['spatial_sd'] = dict(modern=round(float(Mall.std()), 4), zjy=round(float(Zall.std()), 4))
    json.dump(out, open(os.path.join(HERE, f'noise_{scope}.json'), 'w'), indent=1)
    print(f"\n信噪比＝全域空间 SD ÷ 位移 SD。<1 表示挪一下的变化比全城差异还大，图不能读。")
