# -*- coding: utf-8 -*-
"""把 rules_luantou.yaml 每条规则的 quote 拿去原始文本里做核对。
   原文：masters/corpus/gjtsjc/（《欽定古今圖書集成·堪輿部》651–680 卷，公有领域）
   简繁转换用 OpenCC；比对用「最长公共子序列占引文长度之比」，
   ≥0.85 视为属实，0.5–0.85 视为部分吻合（可能是节引或异文），<0.5 视为未找到。"""
import os, re, glob, sys
import yaml
from opencc import OpenCC

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, '..', 'masters', 'corpus', 'gjtsjc')
cc = OpenCC('s2t')

def clean(s):
    return re.sub(r'[^一-鿿]', '', s)

TEXT = {}
for f in sorted(glob.glob(os.path.join(CORPUS, '*.txt'))):
    TEXT[os.path.basename(f)[:-4]] = clean(open(f, encoding='utf8').read())
ALL = ''.join(TEXT.values())

def lcs_ratio(q, t):
    """q 在 t 中的最长公共子序列长度 / len(q)。用滑窗降复杂度。"""
    best = 0
    step = max(1, len(q) // 2)
    for i in range(0, max(1, len(t) - len(q) * 3), step):
        w = t[i:i + len(q) * 3]
        prev = [0] * (len(w) + 1)
        for a in q:
            cur = [0]
            for j, b in enumerate(w):
                cur.append(prev[j] + 1 if a == b else max(cur[j], prev[j + 1]))
            prev = cur
        best = max(best, prev[-1])
        if best == len(q): break
    return best / len(q) if q else 0

def where(q):
    for name, t in TEXT.items():
        if q in t: return name
    return None

d = yaml.safe_load(open(os.path.join(HERE, '..', 'rules_luantou.yaml'), encoding='utf8'))
items = [(r['id'], r.get('quote'), r.get('source')) for r in d.get('rules', [])]
items += [(r['id'], r.get('quote'), r.get('source')) for r in d.get('faults', [])]
items += [(r['id'], r.get('quote'), r.get('source')) for r in (d.get('new_faults') or [])]
items += [(r['id'], r.get('quote'), r.get('source')) for r in (d.get('new_metrics') or [])]

print(f"{'规则':<24}{'比对':>7}  {'落卷':<8}{'标注出处'}")
print('-' * 96)
for rid, q, src in items:
    if not q:
        print(f"{rid:<24}{'无引文':>7}  {'':<8}{src or '(无)'}")
        continue
    for frag in re.split(r'["/／]', str(q)):
        fc = clean(cc.convert(frag))
        if len(fc) < 6: continue
        r = lcs_ratio(fc, ALL)
        loc = where(fc) or ('部分' if r >= .5 else '—')
        mark = '✓' if r >= .85 else ('~' if r >= .5 else '✗')
        print(f"{rid:<24}{r:6.2f}{mark}  {loc:<8}{src or '(无)'}")

# ── 阴性对照：标定噪声底 ────────────────────────────────────────────
# 四句伪造的、风格相似但原文绝无的话。它们的得分即该指标的噪声底。
FAKE = ["穴前三山并起，其气必聚，主子孙昌盛",
        "左有金鸡右有玉犬，中藏紫气，法当大发",
        "水从西北来者，其局必贵，不可轻泄",
        "龙自东南入首，砂水俱备，斯为上吉之地"]
print('\n── 阴性对照（伪造句，用以标定噪声底）──')
for f in FAKE:
    print(f"  {f[:24]:<26}{lcs_ratio(clean(cc.convert(f)), ALL):5.2f}")
print("""
判读标准：
  ≥0.85 且能定位到具体卷 → 属实
  ≥0.85 但只定位到「部分」 → 多半是简繁/异体导致子串失配，需人工确认
  0.5–0.85 → 不足为凭（噪声底约 0.38–0.47）
  <0.5    → 与伪造句同级
该指标对十余字的短引文两个方向都不可靠（既虚高也虚低），只能用来筛，不能用来判。""")
