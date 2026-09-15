# -*- coding: utf-8 -*-
"""哈尔滨地理评分图：两套规则各出一张，外加一张分歧图。

配色按 dataviz 规范：
  - 分数是连续量级 → **单色顺序色阶**（蓝，浅→深）。两张图共用同一色阶与同一绝对刻度，
    否则并排看会把「两套规则的分布不同」误读成「同一块地一高一低」。
  - 分歧是极性量 → **发散色阶**（蓝↔红，中点中性灰）。
  - 河道、地名、等值线一律走文字/中性墨色，不占任何序列色。
"""
import os, sys, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib import font_manager
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))

# 中文字体
for c in ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',):
    if os.path.exists(c):
        font_manager.fontManager.addfont(c)
        plt.rcParams['font.sans-serif'] = [font_manager.FontProperties(fname=c).get_name()]
        break
plt.rcParams['axes.unicode_minus'] = False

# dataviz 参考调色板
SURFACE   = '#fcfcfb'
INK       = '#0b0b0b'
INK2      = '#52514e'
MUTED     = '#8a8983'
BLUE_RAMP = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7',
             '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
SEQ = LinearSegmentedColormap.from_list('seq_blue', BLUE_RAMP)
DIV = LinearSegmentedColormap.from_list('div_br',
        ['#0d366b', '#2a78d6', '#9ec5f4', '#f0efec', '#f0a6a5', '#e34948', '#8f1f1e'])

LANDMARKS_PREF = [
    (45.7565, 126.6424, '哈尔滨主城'),
    (45.8020, 126.5300, '松北'),
    (45.5450, 126.9700, '阿城'),
]
# 市区六个区的政府驻地（OSM place=city 节点）
LANDMARKS_CITY = [
    (45.7930, 126.5086, '松北区'),
    (45.7539, 126.6133, '道里区'),
    (45.7903, 126.6433, '道外区'),
    (45.7581, 126.6626, '南岗区'),
    (45.7062, 126.6569, '香坊区'),
    (45.5957, 126.6311, '平房区'),
    (45.9734, 126.6014, '呼兰区'),
]
LANDMARKS = LANDMARKS_CITY

def load_grid(tag='city'):
    d = json.load(open(os.path.join(HERE, f'grid_{tag}.json'), encoding='utf8'))
    nla, nlo = d['n_lat'], d['n_lon']
    M = np.full((nla, nlo), np.nan)
    Z = np.full((nla, nlo), np.nan)
    meta = np.empty((nla, nlo), object)
    for i, r in enumerate(d['rows']):
        a, b = divmod(i, nlo)
        if r is None: continue
        M[a, b] = r['modern']; Z[a, b] = r['zjy']; meta[a, b] = r
    return d, M, Z, meta

RANK = {'city': 0, 'town': 1, 'suburb': 2, 'county': 2, 'village': 3, 'peak': 4}

def name_of(la, lo, places, maxkm=12.0):
    """给高分区起名：取最近的 OSM 地名，城镇优先于村。"""
    best = None
    for p in places:
        d = math.hypot((p['lat'] - la) * 110.54,
                       (p['lon'] - lo) * 110.54 * math.cos(math.radians(la)))
        if d > maxkm: continue
        k = (RANK.get(p['kind'], 5), d)
        if best is None or k < best[0]:
            best = (k, p, d)
    if best is None: return '', 0.0
    return best[1]['name'], best[2]


def clusters(S, lats, lons, q=90, min_cells=3, top=5):
    """取分位 q 以上的点，连通域聚类，按域内均分排序。"""
    thr = np.nanpercentile(S, q)
    mask = np.nan_to_num(S, nan=-1) >= thr
    lab, n = ndimage.label(mask)
    out = []
    for k in range(1, n + 1):
        m = lab == k
        if m.sum() < min_cells: continue
        ii, jj = np.where(m)
        out.append(dict(n=int(m.sum()),
                        mean=float(np.nanmean(S[m])), max=float(np.nanmax(S[m])),
                        lat=float(np.mean([lats[i] for i in ii])),
                        lon=float(np.mean([lons[j] for j in jj])),
                        lat_max=float(lats[ii[np.argmax(S[m])]]),
                        lon_max=float(lons[jj[np.argmax(S[m])]]),
                        area_km2=float(m.sum() * 1.5 * 1.5)))
    out.sort(key=lambda x: -x['mean'])
    return thr, out[:top], mask


def label_clusters(cl, places):
    for c in cl:
        c['place'], c['place_km'] = name_of(c['lat'], c['lon'], places)
        c['place_max'], _ = name_of(c['lat_max'], c['lon_max'], places)
    return cl

def draw(ax, S, d, title, sub, norm, cmap, ways, places, mark=True, q=90,
         districts=None):
    lats, lons = np.array(d['lats']), np.array(d['lons'])
    dla = (lats[1] - lats[0]) / 2; dlo = (lons[1] - lons[0]) / 2
    ext = [lons[0] - dlo, lons[-1] + dlo, lats[0] - dla, lats[-1] + dla]
    ax.imshow(S, origin='lower', extent=ext, cmap=cmap, norm=norm,
              interpolation='bilinear', aspect=1 / math.cos(math.radians(lats.mean())))
    # 行政区界
    for dst in (districts or []):
        for ring in dst['rings']:
            r = np.array(ring)
            ax.plot(r[:, 1], r[:, 0], lw=0.9, color=INK, alpha=.55, zorder=3.5)
    # 河道
    for w in ways:
        p = np.array(w['pts'])
        gan = w.get('_gan')
        ax.plot(p[:, 1], p[:, 0], lw=3.0 if gan else 1.1,
                color='#ffffff', alpha=.9 if gan else .55,
                zorder=3, solid_capstyle='round')
        ax.plot(p[:, 1], p[:, 0], lw=1.5 if gan else 0.4,
                color='#1a1a19' if gan else '#6b6a64',
                alpha=.9 if gan else .6, zorder=3.1, solid_capstyle='round')
    # 高分区
    if mark:
        thr, cl, mask = clusters(S, lats, lons, q=q)
        cl = label_clusters(cl, places)
        ax.contour(lons, lats, mask.astype(float), levels=[.5],
                   colors=[INK], linewidths=1.1, zorder=4)
        for i, c in enumerate(cl, 1):
            ax.plot(c['lon'], c['lat'], 'o', ms=15, mfc=SURFACE, mec=INK,
                    mew=1.2, zorder=6)
            ax.text(c['lon'], c['lat'], str(i), ha='center', va='center',
                    fontsize=9, color=INK, zorder=7, fontweight='bold')
            if c.get('place'):
                # 标注甩向图幅内侧，避免右缘的高分区把文字甩出画面
                fx = (c['lon'] - ext[0]) / (ext[1] - ext[0])
                fy = (c['lat'] - ext[2]) / (ext[3] - ext[2])
                dx = -22 if fx > .62 else 16
                ha = 'right' if fx > .62 else 'left'
                dy = (20 if fy < .5 else -20) + (i - 1) * (14 if fy < .5 else -14)
                ax.annotate(f"{i} {c['place']}", (c['lon'], c['lat']),
                            textcoords='offset points', xytext=(dx, dy), ha=ha,
                            fontsize=8.5, color=INK, zorder=7,
                            arrowprops=dict(arrowstyle='-', lw=.6, color=INK2,
                                            shrinkA=8, shrinkB=1),
                            bbox=dict(fc=SURFACE, ec='#dcdbd6', lw=.5, alpha=.92, pad=1.6))
    # 地名
    for la, lo, nm in LANDMARKS:
        if not (ext[0] < lo < ext[1] and ext[2] < la < ext[3]): continue
        ax.plot(lo, la, marker='s', ms=3.5, color=INK, zorder=5)
        ax.text(lo + .015, la, nm, fontsize=9, color=INK, zorder=5,
                va='center', path_effects=None,
                bbox=dict(fc=SURFACE, ec='none', alpha=.75, pad=1.2))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
    ax.set_title(title, fontsize=14, color=INK, pad=38, loc='left')
    ax.text(0, 1.012, sub, transform=ax.transAxes, fontsize=8.6, color=INK2,
            va='bottom', ha='left', linespacing=1.35)
    ax.set_xlabel('东经 °', fontsize=8, color=INK2)
    ax.set_ylabel('北纬 °', fontsize=8, color=INK2)
    ax.tick_params(labelsize=7.5, colors=INK2, length=2)
    for s in ax.spines.values(): s.set_color('#dcdbd6')
    # 比例尺
    km = 20.0
    dlon_km = km * 1000 / (111320 * math.cos(math.radians(lats.mean())))
    x0 = ext[0] + (ext[1] - ext[0]) * .06; y0 = ext[2] + (ext[3] - ext[2]) * .05
    ax.plot([x0, x0 + dlon_km], [y0, y0], color=INK, lw=2.2, zorder=8,
            solid_capstyle='butt')
    ax.text(x0 + dlon_km / 2, y0 + (ext[3] - ext[2]) * .012, f'{km:.0f} km',
            ha='center', fontsize=7.5, color=INK, zorder=8)
    if mark:
        thr2, cl2, msk2 = clusters(S, lats, lons, q=q)
        return thr2, label_clusters(cl2, places), msk2
    return (None, [], None)

if __name__ == '__main__':
    scope = sys.argv[1] if len(sys.argv) > 1 else 'city'
    if scope == 'prefecture':
        LANDMARKS = LANDMARKS_PREF
    d, M, Z, meta = load_grid(scope)
    ways = json.load(open(os.path.join(HERE, 'osm_rivers_harbin.json'), encoding='utf8'))
    # 标出哪些是「幹」：与 attach_external_rivers 同一判据
    from collections import defaultdict
    sl = defaultdict(float)
    for w in ways:
        p = w['pts']
        for a, b in zip(p[:-1], p[1:]):
            sl[w.get('name') or id(w)] += math.hypot(
                (b[0]-a[0])*110540, (b[1]-a[1])*110540*math.cos(math.radians(a[0])))/1000
    for w in ways:
        w['_gan'] = (w.get('kind') == 'river'
                     and sl[w.get('name') or id(w)] >= 90.0)
    pf = os.path.join(HERE, 'osm_places_harbin.json')
    places = json.load(open(pf, encoding='utf8')) if os.path.exists(pf) else []
    df = os.path.join(HERE, 'districts.json')
    districts = json.load(open(df, encoding='utf8')) if os.path.exists(df) else None
    nf = os.path.join(HERE, f'noise_{scope}.json')
    noise = json.load(open(nf, encoding='utf8')) if os.path.exists(nf) else None

    lo_, hi_ = np.nanpercentile(np.concatenate([M.ravel(), Z.ravel()]), [1, 99.5])
    norm = Normalize(lo_, hi_)

    fig, axes = plt.subplots(1, 3, figsize=(21.5, 9.4), facecolor=SURFACE)
    for a in axes: a.set_facecolor(SURFACE)

    _, cl_m, _ = draw(axes[0], M, d, '① 现代版规则 v1.1',
        'A 级骨架＋B 级十三条（含《水龙经》平洋法）\n平洋模式下玄武／护龙不计分，势形改用干／支',
        norm, SEQ, ways, places, districts=districts)
    _, cl_z, _ = draw(axes[1], Z, d, '② 《葬經翼》本（约 1600）',
        '只用繆希雍一部书：四兽砂水、明堂、水口、穴病七条\n本书无平洋法，故在平原上照用山龙判据——这正是《水龙经》点名的「傅會山龍之妄說」',
        norm, SEQ, ways, places, districts=districts)

    # 分歧：两套规则各自的分位之差
    def pct(S):
        v = S[~np.isnan(S)]
        r = np.full(S.shape, np.nan)
        order = v.argsort().argsort() / (len(v) - 1)
        r[~np.isnan(S)] = order
        return r
    D = pct(M) - pct(Z)
    m = np.nanmax(np.abs(D))
    draw(axes[2], D, d, '③ 两套规则的分歧',
         '同一点在各自分布中的分位之差\n蓝＝现代版更看好，红＝《葬經翼》更看好',
         TwoSlopeNorm(vmin=-m, vcenter=0, vmax=m), DIV, ways, places, mark=False,
         districts=districts)

    # 色标
    cax = fig.add_axes([0.06, 0.045, 0.30, 0.016])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=SEQ), cax=cax,
                      orientation='horizontal')
    cb.set_label('形势总分（①②共用同一绝对刻度）', fontsize=8.5, color=INK2)
    cb.ax.tick_params(labelsize=7.5, colors=INK2, length=2)
    cb.outline.set_visible(False)
    cax2 = fig.add_axes([0.70, 0.045, 0.22, 0.016])
    cb2 = fig.colorbar(plt.cm.ScalarMappable(norm=TwoSlopeNorm(vmin=-m, vcenter=0, vmax=m), cmap=DIV),
                       cax=cax2, orientation='horizontal')
    cb2.set_label('分位之差', fontsize=8.5, color=INK2)
    cb2.ax.tick_params(labelsize=7.5, colors=INK2, length=2)
    cb2.outline.set_visible(False)

    TITLE = {'city': '哈尔滨市区形势评分：两套规则对照（松北・主城・平房）',
             'prefecture': '哈尔滨地级市形势评分：两套规则对照'}[scope]
    fig.suptitle(TITLE,
                 fontsize=18, color=INK, x=0.045, ha='left', y=0.975)
    cap = ('黑线圈出各自的前 10% 区域，编号见图内标注。灰细线为区界，粗线为「幹」（松花江、阿什河等），细线为支水沟渠。'
           '\n分数没有经过效度检验：同一套规则在八个已知被选中的古代样本上，本地分位均值 0.515（零假设 0.500）。此图是规则的计算结果，不是选址建议。')
    if noise:
        n5 = noise.get('500.0') or noise.get('500')
        if n5:
            cap += ('\n**位移噪声底**：把穴位挪 500 m，现代版分数平均变 %.3f、《葬經翼》变 %.3f，'
                    '而全市区空间 SD 分别是 %.3f / %.3f（信噪比 %.1f / %.1f）。'
                    '**只能读大片格局，不能读单个格子**；两处相差不到约 0.05 即无意义。'
                    % (n5['modern_sd'], n5['zjy_sd'],
                       noise['spatial_sd']['modern'], noise['spatial_sd']['zjy'],
                       n5['modern_snr'], n5['zjy_snr']))
    fig.text(0.045, 0.940, cap.replace('**', ''),
             fontsize=9, color=INK2, ha='left', va='top', linespacing=1.5)
    fig.subplots_adjust(left=.045, right=.985, top=.845, bottom=.105, wspace=.14)
    out = os.path.join(HERE, f'harbin_{scope}.png')
    fig.savefig(out, dpi=140, facecolor=SURFACE)
    print('→', out)

    json.dump(dict(modern=cl_m, zangjingyi=cl_z),
              open(os.path.join(HERE, f'top_areas_{scope}.json'), 'w', encoding='utf8'),
              ensure_ascii=False, indent=1)
    # 每个区自己的最高处
    rows = [r for r in d['rows'] if r]
    if rows and rows[0].get('district'):
        for tag, key in (('现代版 v1.1', 'modern'), ('葬經翼本', 'zjy')):
            print(f'\n{tag}：各区自己的最高处')
            byd = {}
            for r in rows:
                k = r['district']
                if k and (k not in byd or r[key] > byd[k][key]): byd[k] = r
            for k, r in sorted(byd.items(), key=lambda x: -x[1][key]):
                nm, _ = name_of(r['lat'], r['lon'], places)
                print(f"  {k:<6}{r[key]:.3f}  {r['lat']:.3f}N {r['lon']:.3f}E  近 {nm}"
                      f"  ({r['py_class']})")

    for tag, cl in (('现代版 v1.1', cl_m), ('葬經翼本', cl_z)):
        print(f'\n{tag} 前 10% 区域（按域内均分排序）')
        for i, c in enumerate(cl, 1):
            print(f"  {i}. {c.get('place',''):<10} {c['lat']:.3f}N {c['lon']:.3f}E  "
                  f"均分 {c['mean']:.3f} 峰值 {c['max']:.3f} "
                  f"面积约 {c['area_km2']:.0f} km²  峰值点近 {c.get('place_max','')}")
