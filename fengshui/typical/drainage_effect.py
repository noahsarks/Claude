# -*- coding: utf-8 -*-
"""把「改规则」与「修 bug」两件事的影响分开量。

run.py 的两列都跑在 v0.8 的汇流网络上，所以它的 Δ 只反映规则改动。
但 v0.8 还修了平地导流这个 bug，而 bug 修完水系整个变了。
这里让同一套 v0.6 规则分别跑在修前、修后的网络上，单独量 bug 的影响。
"""
import sys, os, importlib, yaml, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
S = yaml.safe_load(open(os.path.join(HERE, 'sites.yaml'), encoding='utf8'))['sites']

def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m

def run_with(engine_path, score_path):
    """engine_path 决定汇流网络（kvamme.Mosaic 继承它的 Region），
       score_path 决定打分规则。两者可以不同。"""
    import kvamme as K
    L = load(engine_path, 'luantou'); sys.modules['luantou'] = L
    importlib.reload(K)
    SC = L if score_path == engine_path else load(score_path, '_sc')
    out = {}
    for s in S:
        reg = K.Mosaic('x', range(int(s['lat']), int(s['lat'])+1),
                           range(int(s['lon']), int(s['lon'])+1))
        M = SC.metrics(reg, s['lat'], s['lon'], theta_deg=s['坐'])
        out[s['name']] = SC.score(M)['final'] if M else None
    return out

if __name__ == '__main__':
    v6 = os.path.join(REPO, 'luantou_v6.py')
    v8 = os.path.join(REPO, 'luantou.py')
    a = run_with(v6, v6)          # 旧网络 + 旧规则
    b = run_with(v8, v6)          # 新网络 + 旧规则  ← 只差一个 bug 修复
    c = run_with(v8, v8)          # 新网络 + 新规则
    print(f"{'点':<18}{'旧网旧规':>9}{'新网旧规':>9}{'Δbug':>8}{'新网新规':>9}{'Δ规则':>8}")
    db, dr = [], []
    for k in a:
        if None in (a[k], b[k], c[k]): print(f'{k:<18} 有点算不出'); continue
        db.append(b[k]-a[k]); dr.append(c[k]-b[k])
        print(f"{k:<18}{a[k]:9.3f}{b[k]:9.3f}{b[k]-a[k]:+8.3f}{c[k]:9.3f}{c[k]-b[k]:+8.3f}")
    print(f"\n平均绝对变化：修 bug {np.mean(np.abs(db)):.3f}　改规则 {np.mean(np.abs(dr)):.3f}")
