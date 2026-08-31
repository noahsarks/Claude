"""事后分层匹配：把每个正样本只与同高程带、同起伏度带的背景点比，去掉地形可达性混淆。"""
import json, glob, numpy as np, math
from scipy import stats

def load(tag):
    return (json.load(open(f'out/bg_{tag}.json')), json.load(open(f'out/pos_{tag}.json')))

def kv(area_pct, site_pct):
    return 1 - area_pct/site_pct if site_pct > 0 else float('-inf')

def analyse(tag):
    BG, POS = load(tag)
    bs = np.array([b['score'] for b in BG])
    bh = np.array([b['h'] for b in BG]); br = np.array([b['relief'] for b in BG])
    out = {'tag': tag, 'n_bg': len(BG)}
    for kind in ('all', 'tomb', 'building'):
        P = POS if kind == 'all' else [p for p in POS if p['k'] == kind]
        if len(P) < 8: continue
        ps = np.array([p['score'] for p in P])
        # 原始背景
        auc_raw = float(np.mean([(bs < v).mean() + .5*(bs == v).mean() for v in ps]))
        th = [np.percentile(bs, q) for q in (95, 80)]
        site_hi = 100*float(np.mean(ps >= th[1]))
        # 分层匹配：同高程 ±150m 且起伏度 0.6–1.7 倍
        pct_m, used = [], 0
        for p in P:
            m = (np.abs(bh - p['h']) <= 150) & (br >= .6*p['relief']) & (br <= 1.7*p['relief'])
            if m.sum() < 25: continue
            used += 1
            pct_m.append(float((bs[m] < p['score']).mean()))
        pct_m = np.array(pct_m)
        auc_m = float(pct_m.mean()) if len(pct_m) else float('nan')
        # 匹配口径下的"高潜力区"= 各自分层内的前 20%
        site_hi_m = 100*float((pct_m >= .80).mean()) if len(pct_m) else float('nan')
        u = stats.mannwhitneyu(ps, bs, alternative='two-sided')
        out[kind] = dict(n=len(P), mean=float(ps.mean()), bg_mean=float(bs.mean()),
                         auc_raw=auc_raw, gain_raw=kv(20, site_hi), site_hi=site_hi,
                         n_matched=used, auc_matched=auc_m,
                         gain_matched=kv(20, site_hi_m), site_hi_matched=site_hi_m,
                         mw_p=float(u.pvalue))
    return out

if __name__ == '__main__':
    tags = [f.split('bg_')[1].split('.json')[0] for f in sorted(glob.glob('out/bg_*.json'))]
    R = [analyse(t) for t in tags]
    json.dump(R, open('out/matched.json', 'w'), ensure_ascii=False, indent=1, default=float)
    for r in R:
        print(f"\n=== {r['tag']}  背景 n={r['n_bg']}")
        print(f"{'类别':10s}{'n':>5s}{'均分':>7s}{'背景均分':>9s}{'AUC原始':>9s}{'AUC匹配':>9s}{'增益原始':>9s}{'增益匹配':>9s}{'MW-p':>10s}")
        for k in ('all', 'tomb', 'building'):
            if k not in r: continue
            d = r[k]
            print(f"{k:10s}{d['n']:5d}{d['mean']:7.3f}{d['bg_mean']:9.3f}"
                  f"{d['auc_raw']:9.3f}{d['auc_matched']:9.3f}"
                  f"{d['gain_raw']:9.3f}{d['gain_matched']:9.3f}{d['mw_p']:10.2e}")
