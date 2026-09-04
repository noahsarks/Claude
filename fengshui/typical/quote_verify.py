# -*- coding: utf-8 -*-
"""把 CHRONOLOGY.md 与 MODERN_RULES.yaml 里的每一条引文，逐条拿去语料里找。

起因：写编年时我给呂才那段补了一句「亦有子孫昌盛者，亦有國滅家亡者」——
原文没有，是我脑补的。这类错自己读不出来，只能机械核。

判据：把引文按标点切成片段，每段（长度≥6）在语料里做子串查找。
简繁与避讳（玄→元）先归一。全部片段命中才算「属实」。
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(os.path.dirname(HERE), 'masters', 'corpus', 'gjtsjc')

CORPUS = ''
for n in range(651, 681):
    CORPUS += open(os.path.join(G, f'{n}.txt'), encoding='utf8').read()

def norm(t):
    t = re.sub(r'\*\*|\*|`|~~', '', t)                     # 去 markdown 强调
    t = re.sub(r'[，。、；：？！「」『』《》〈〉…—\s（）()　]', '', t)
    return t.replace('玄', '元')          # 殿本避康熙帝諱

CN = norm(CORPUS)

SIMP = set('这个说体样识对应关实证据术数为国时间条现规则计算网络汉魏义级层们没错读')
# 故意列举「语料里没有的词」的几处，本身就不是引文，单独放行
ALLOW = {'三元九運 + 二十四山分陰陽順逆 + 挨星起星 + 山盤向盤雙飛',
         '但「三元九運 + 二十四山分陰陽順逆 + 挨星起星 + 山盤向盤雙飛」',
         '亦有子孫昌盛者，亦有國滅家亡者'}   # 最后一条是我脑补又删掉的那句，留作记录

def is_prose(q):
    """我自己的白话转述：含简体专用字、拉丁字母、阿拉伯数字或箭头，即判为转述。"""
    qq = re.sub(r'\*\*|\*|`', '', q)
    if qq in ALLOW or q in ALLOW: return True
    return bool(re.search(r'[A-Za-z0-9→＋+]', qq)) or any(c in SIMP for c in qq)

def check(q):
    """返回 (命中片段数, 总片段数, 未命中的片段)"""
    q = re.sub(r'\*\*|\*|`', '', q)
    seg = re.split(r'[，。、；：？！…\s]+', q)
    parts = [p for p in seg if len(p) >= 6]
    if not parts:                       # 短句连引（如「詰曰：……據見而用？」）放宽到 3 字
        parts = [p for p in seg if len(p) >= 3] or [q]
    miss = [p for p in parts if norm(p) not in CN]
    return len(parts) - len(miss), len(parts), miss

def quotes_from_md(path):
    out = []
    for ln in open(path, encoding='utf8'):
        ln = ln.rstrip('\n')
        m = re.match(r'^>\s?(.+)$', ln)                      # 引用块
        if m and re.search(r'[一-鿿]', m.group(1)):
            out.append(('引用块', m.group(1)))
        for g in re.findall(r'「([^」]{6,})」', ln):          # 行内「」
            out.append(('行内', g))
    return out

def quotes_from_yaml(path):
    import yaml
    d = yaml.safe_load(open(path, encoding='utf8'))
    out = []
    def walk(o, k=''):
        if isinstance(o, dict):
            for a, b in o.items(): walk(b, str(a))
        elif isinstance(o, list):
            for x in o: walk(x, k)
        elif isinstance(o, str) and k.startswith('quote'):
            out.append((k, o))
    walk(d)
    return out

if __name__ == '__main__':
    targets = []
    md = os.path.join(HERE, 'CHRONOLOGY.md')
    if os.path.exists(md): targets += [(md, q) for q in quotes_from_md(md)]
    for y in ('MODERN_RULES.yaml',):
        p = os.path.join(HERE, y)
        if os.path.exists(p): targets += [(p, q) for q in quotes_from_yaml(p)]
    bad = []; prose = 0; ok = 0
    seen = set()
    for path, (kind, q) in targets:
        if q in seen: continue
        seen.add(q)
        if is_prose(q):
            prose += 1; continue                 # 我自己的话，不当引文核
        hit, tot, miss = check(q)
        if miss:
            bad.append((os.path.basename(path), kind, q, hit, tot, miss))
        else:
            ok += 1
    for f, kind, q, hit, tot, miss in bad:
        print(f"✗ [{f} {kind}] {hit}/{tot}  {q[:44]}")
        for m in miss[:3]:
            print(f"     未命中：{m}")
    print(f"\n候选 {len(seen)} 条：判为我的转述 {prose} 条，按引文核 {ok+len(bad)} 条，"
          f"其中全部命中 {ok} 条，有未命中 {len(bad)} 条。")
    if bad:
        print("未命中不等于伪造（可能跨行断句），但每一条都必须人工看过再留。")
    sys.exit(0)
