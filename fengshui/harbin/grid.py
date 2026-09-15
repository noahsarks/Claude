# -*- coding: utf-8 -*-
"""哈尔滨地理评分格网：同一套地形指标，两套规则分别打分。

两套规则的定义见本文件 score_modern / score_zangjingyi，
依据 ../typical/MODERN_RULES.yaml。

  ① 现代版 v1.1  —— 引擎 v0.8 原样：A 级骨架 + B 级十三条（含《水龙经》平洋法）
                    + D 级标为估值的权重。平洋模式下玄武/护龙归零、势形改用干/支。
  ② 葬经翼本     —— 只用《欽定古今圖書集成》卷 670 繆希雍《葬經翼》一部书里的条目。
                    选它的理由见 README：它是全部技术文献里年代最可靠的一部
                    （约 1600，作者生卒可考），而技术文献 66.1% 是托名。

坐向：B1「擇向」说坐向是输入不是从地形反推。做区域普查没有逐点坐向，
      故统一假设**坐北朝南**（theta=0），并单独跑一遍「坐向不判」作敏感性对照。
"""
import os, sys, math, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import importlib.util

def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m

L = load(os.path.join(REPO, 'luantou.py'), 'luantou')
sys.modules['luantou'] = L
import kvamme as K

pl = L.pl
ramp = L.ramp

# ── 规则集 ②：《葬經翼》本 ──────────────────────────────────────────
# 取哪些、不取哪些，逐条给理由（篇名据 ../rules_audit/ 与 ../typical/MODERN_RULES.yaml）
ZJY_USE = {
    'xuanwu':     ('四獸砂水篇「元武垂頭」；原勢篇、察形篇', .15),
    'hulong':     ('四獸砂水篇「青龍蜿蜒，白虎馴頫」「環抱有情，不逼不壓」', .11),
    'xiangbei':   ('四獸砂水篇論向背', .12),
    'mingtang':   ('明堂篇「明堂者，穴前水聚處也」及水的四級序', .18),
    'water_gate': ('水口篇「若結都會及作帝王山陵，必有北辰尊星坐鎮水口」', .09),
}
ZJY_DROP = {
    'water':    '得水分量的指标组合出自《博山篇·論水》与无定河实证，非本书',
    'zangfeng': '「藏風」出自《葬經·氣感篇》，非本书',
    'pingyang': '平洋法出自《水龍經》（17 世纪），本书成书约 1600，无此内容',
}
ZJY_FAULTS = {'拒尸(玄武不垂)', '断山(坠足)', '折臂', '割脚',
              '虎蹲(衔尸)', '龙踞(嫉主)', '朱雀腾去'}      # 穴病篇十五条里已实现的七条
ZJY_FAULT_DROP = {'过山(势未止)': '《葬經》五不葬，非本书',
                  '独山(气不会)': '《葬經》五不葬，非本书',
                  '干水散气':   '《水龍經·幹水散氣圖說》，非本书'}

def score_modern(M):
    return L.score(M)

def score_zangjingyi(M):
    """只用《葬經翼》一部书里的条目。

    与现代版的三处关键差别：
      1. **不分平洋**——本书通篇论山龙，没有平洋法，也就没有「平陽大地無龍虎」那一条。
         所以在平原上它照样用玄武、护龙打分。这正是《水龍經》序里点名的
         「傅會山龍之妄說」，此处如实照做，不替古人打补丁。
      2. 不含得水、藏风两个分量（出处不在本书）。
      3. 凶格只用穴病篇的七条。
    """
    if M is None: return None
    full = L.score(M)
    if full is None: return None
    c = full['components']
    w = {k: v[1] for k, v in ZJY_USE.items()}
    s = sum(w.values())
    base = sum(w[k] / s * min(max(c[k], 0), 1) for k in w)
    # 势与形：《葬經翼》首二篇即「原勢」「察形」，沿用《葬經》「勢與形順者吉」的乘性关系。
    # 但势的构成里去掉水口以外的非本书项，形的构成里去掉得水。
    shi = .60 * c['xuanwu'] + .40 * c['water_gate']
    xing = .55 * c['mingtang'] + .45 * c['xiangbei']
    gap = shi - xing
    mism = 1 - min(1.0, (-gap) * 1.30) if gap < 0 else 1 - min(1.0, gap * 0.75)
    mism = max(mism, 0.15)
    disc = 1.0
    F = {k: v for k, v in full['faults'].items() if k in ZJY_FAULTS}
    for v in F.values(): disc *= (1 - v)
    return dict(components={k: c[k] for k in w}, base=base, mismatch=mism,
                faults=F, final=base * mism * disc, mode='山龙(本书不分平洋)')

# ── 格网 ────────────────────────────────────────────────────────────
# 两个范围。默认是 city——用户要的是**市区**（松北、平房、主城），
# 而不是整个地级市；阿城、玉泉在地级市内但不在市区，第一版把框拉到那边去了。
SCOPES = {
    'city':       dict(box=dict(lat0=45.52, lat1=46.10, lon0=126.14, lon1=127.12),
                       step=750.0, mask='districts',
                       desc='哈尔滨市区：松北、道里、南岗、道外、香坊、平房六区'
                            '（框取六区外接矩形，再按行政边界裁）'),
    'prefecture': dict(box=dict(lat0=45.35, lat1=46.15, lon0=126.00, lon1=127.30),
                       step=1500.0,
                       desc='地级市范围（含阿城、玉泉），第一版用的框'),
}
BOX = SCOPES['city']['box']
STEP_M = SCOPES['city']['step']

def build(theta_deg=0.0, tag='city', mask=None):
    reg = K.Mosaic('harbin', range(45, 47), range(125, 128))
    # 接外部水系：松花江上游在瓦片外，DEM 汇流累积在瓦片内看不出它是「幹」，
    # 引擎会正确弃权，但平洋法第一条就用不上。故拿 OSM 实测河道给「幹」。
    ways = json.load(open(os.path.join(HERE, 'osm_rivers_harbin.json'), encoding='utf8'))
    info = L.attach_external_rivers(reg, ways)
    print(f"外部水系：{info['n_pts']} 节点，干水 {info['n_gan']}；"
          f"判为幹的水道 {info['gan_names']}", flush=True)
    dlat = STEP_M / 110540.0
    clat = (BOX['lat0'] + BOX['lat1']) / 2
    dlon = STEP_M / (111320.0 * math.cos(math.radians(clat)))
    lats = np.arange(BOX['lat0'], BOX['lat1'], dlat)
    lons = np.arange(BOX['lon0'], BOX['lon1'], dlon)
    D = None
    if mask == 'districts':
        from districts_mask import Districts
        D = Districts()
        print('按行政边界裁：', ', '.join(D.paths), flush=True)
    print(f'格网 {len(lats)} × {len(lons)} = {len(lats)*len(lons)} 点，'
          f'步长 {STEP_M:.0f} m，坐向 {theta_deg}', flush=True)
    rows = []
    t0 = time.time()
    for i, la in enumerate(lats):
        for lo in lons:
            dist = D.which(float(la), float(lo)) if D is not None else None
            if D is not None and dist is None:
                rows.append(None); continue          # 区外不算
            try:
                M = L.metrics(reg, float(la), float(lo), theta_deg=theta_deg)
            except Exception:
                M = None
            if M is None:
                rows.append(None); continue
            a = score_modern(M); b = score_zangjingyi(M)
            rows.append(dict(lat=float(la), lon=float(lo), district=dist,
                             h=float(M['h0']) if 'h0' in M else None,
                             relief=float(M['relief_3km']), landform=M.get('landform'),
                             mode=a['mode'], py_class=M.get('py_class'),
                             modern=round(a['final'], 4),
                             zjy=round(b['final'], 4),
                             py=None if M.get('py') is None else round(M['py'], 3),
                             wrap=round(M.get('py_wrap', 0), 3),
                             bends=int(M.get('py_bends', 0)),
                             mc={k: round(v, 3) for k, v in a['components'].items()},
                             zc={k: round(v, 3) for k, v in b['components'].items()},
                             mf=list(a['faults']), zf=list(b['faults'])))
        if i % 5 == 0:
            print(f'  row {i+1}/{len(lats)}  {time.time()-t0:.0f}s', flush=True)
    out = dict(box=BOX, step_m=STEP_M, theta=theta_deg, mask=mask,
               n_lat=len(lats), n_lon=len(lons),
               lats=[float(x) for x in lats], lons=[float(x) for x in lons],
               rows=rows)
    p = os.path.join(HERE, f'grid_{tag}.json')
    json.dump(out, open(p, 'w', encoding='utf8'), ensure_ascii=False)
    print(f'→ {p}  有效点 {sum(1 for r in rows if r)}/{len(rows)}  '
          f'用时 {time.time()-t0:.0f}s')
    return out

if __name__ == '__main__':
    scope = sys.argv[1] if len(sys.argv) > 1 else 'city'
    globals()['BOX'] = SCOPES[scope]['box']
    globals()['STEP_M'] = SCOPES[scope]['step']
    print(SCOPES[scope]['desc'])
    build(0.0, scope, SCOPES[scope].get('mask'))
