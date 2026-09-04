# -*- coding: utf-8 -*-
"""典型建筑验证：v0.6（旧）vs v0.8（现）逐点对照。

v0.7 三处规则改动：① 删去龙虎左右对称项（原文无依据）
                   ② 明堂补入水项（「明堂者，穴前水聚处也」四级序），坐向未知则不判
                   ③ R3 环带按「不拘远近」放宽 0.3–3km → 0.1–4km
v0.8 两处：        ④ 补《水龙经》平洋法（支干、回头环绕、屈曲、停蓄），判不了则不判
                   ⑤ **修平地导流**——填洼造出的严格平地上 D8 给不出方向，汇流在此中断。
                      这一条不是规则改动，是 bug；它把此前所有涉水指标都算错了。
                      外部校核见 river_check.py。"""
import sys, os, math, yaml
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import importlib, numpy as np
import kvamme as K

HERE = os.path.dirname(os.path.abspath(__file__))
S = yaml.safe_load(open(os.path.join(HERE, 'sites.yaml'), encoding='utf8'))['sites']

def load(mod_path, name):
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m

REPO = os.path.dirname(HERE)                      # 引擎与本目录同在仓库内
V6 = load(os.path.join(REPO, 'luantou_v6.py'), 'lt_v6')
V7 = load(os.path.join(REPO, 'luantou.py'),   'lt_v8')

regs = {}
def region(lat, lon):
    k = (int(lat), int(lon))
    if k not in regs:
        regs[k] = K.Mosaic(f'{k}', range(k[0], k[0]+1), range(k[1], k[1]+1))
    return regs[k]

print(f"{'点':<18}{'对象':<8}{'坐':>5}  {'v0.6':>7}{'v0.8':>7}{'Δ':>7}  {'明堂6→8':>14}  水类")
print('-'*92)
rows = []
for s in S:
    reg = region(s['lat'], s['lon'])
    th = s['坐']
    try:
        m6 = V6.metrics(reg, s['lat'], s['lon'], theta_deg=th)
        r6 = V6.score(m6)
        m7 = V7.metrics(reg, s['lat'], s['lon'], theta_deg=th)
        r7 = V7.score(m7)
    except Exception as e:
        print(f"{s['name']:<18}计算失败 {e}"); continue
    mt6, mt7 = r6['components']['mingtang'], r7['components']['mingtang']
    rows.append((s, r6, r7, m7))
    print(f"{s['name']:<18}{s['对象']:<8}{str(th):>5}  {r6['final']:7.3f}{r7['final']:7.3f}"
          f"{r7['final']-r6['final']:+7.3f}  {mt6:6.3f}→{mt7:6.3f}  {m7.get('mt_class','')}")

print(f"\n{'点':<18}" + ''.join(f"{k[:4]:>8}" for k in
      ('xuanwu','hulong','xiangbei','mingtang','water','water_gate','zangfeng')))
for s, r6, r7, m7 in rows:
    c = r7['components']
    print(f"{s['name']:<18}" + ''.join(f"{c[k]:8.3f}" for k in
          ('xuanwu','hulong','xiangbei','mingtang','water','water_gate','zangfeng')))

# 本地背景分位另见 bg.py（同一坐向、半径 15 km、400 随机点的经验分位）。
import json
json.dump([{ 'name': s0['name'], '对象': s0['对象'], '坐': s0['坐'],
             'v06': round(r6['final'],4), 'v08': round(r7['final'],4),
             'mt_class': m7.get('mt_class'),
             'comp': {k: round(v,4) for k, v in r7['components'].items()},
             'faults': list(r7['faults'])}
           for s0, r6, r7, m7 in rows],
          open(os.path.join(HERE,'results.json'),'w',encoding='utf8'),
          ensure_ascii=False, indent=1)
print('\n→ results.json')
