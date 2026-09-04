# -*- coding: utf-8 -*-
"""按**实际成书年代**（不是卷次、不是题署）分层，追踪每个概念最早出现在哪一层。

为什么不能按卷次：卷次是《集成》馆臣的编排，把托名汉晋的书排在前面。
为什么不能按题署：托名占技术文献 66%，按题署排会得出
「东汉已有完整体系，后世只是注解」的错误图景。

分层依据 works.yaml。卷 665 内含两书（郭璞葬經 S4 / 青囊奧旨 S5），按标题切开。
"""
import os, re, yaml
from collections import OrderedDict
HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(os.path.dirname(HERE), 'masters', 'corpus', 'gjtsjc')

def raw(n):
    t = open(os.path.join(G, f'{n}.txt'), encoding='utf8').read()
    i = t.find('[编辑]')
    return t[i:] if i > 0 else t

# 层：(代号, 说明, [卷…])  ——「确定」层与「托名」层分开标
STRATA = OrderedDict([
 ('S1 东汉·确定',      dict(desc='王充《論衡》三篇（约 80）——**批判**', juan=[('679a', None)])),
 ('S2 魏晋·确定',      dict(desc='嵇康《難宅無吉凶攝生論》（3 世纪）——**批判**', juan=[('680a', None)])),
 ('S3 唐 640·确定',    dict(desc='呂才《五行祿命葬書論》——**批判**', juan=[('680b', None)])),
 ('S4 唐宋·托名',      dict(desc='郭璞葬經、青烏葬經、管氏指蒙——技术骨架层',
                            juan=[(655, None), ('665a', None)] + [(j, None) for j in range(656, 665)])),
 ('S5 宋元·托名存疑',  dict(desc='青囊海角經、青囊奧旨、十二杖法、博山篇、廖禹十六葬法等、五星捉脈',
                            juan=[(j, None) for j in (651, 652, 653, 654)] + [('665b', None), (666, None), (667, None), (668, None)])),
 ('S6 元末明初',       dict(desc='劉基堪輿漫興；趙汸、胡翰（批判）', juan=[(669, None), ('680c', None)])),
 ('S7 明·确定',        dict(desc='繆希雍葬經翼（约 1600）、陽宅十書（约 1590）、羅虞臣項喬（批判）',
                            juan=[(670, None), (675, None), (676, None), (677, None), (678, None), ('680d', None)])),
 ('S8 明末清初·编次',  dict(desc='水龍經（蔣大鴻編次）', juan=[(j, None) for j in (671, 672, 673, 674)])),
 ('S9 清 1726',        dict(desc='名流列傳、紀事、雜錄（館臣所輯）', juan=[('679b', None), ('680e', None)])),
])

def split_665():
    t = raw(665); i = t.find('楊筠松青囊奧旨', 200)
    return t[:i], t[i:]

def split_680():
    t = raw(680)
    def cut(a, b):
        # 用《》形的正文标题切；目录里的标题不带书名号，故不会误切
        i = t.find(a); j = t.find(b) if b else len(t)
        return t[i:j] if 0 <= i < j else ''
    return (cut('《難宅無吉凶攝生論》', '《五行祿命葬書論》'),   # a 嵇康（含答釋難）
            cut('《五行祿命葬書論》', '《葬書問對》'),           # b 呂才 640
            cut('《葬書問對》', '《辨惑論》'),                   # c 趙汸 + 胡翰
            cut('《辨惑論》', '堪輿部紀事'),                     # d 羅虞臣 + 項喬
            t[t.rfind('堪輿部紀事'):])                          # e 紀事 + 雜錄

def split_679():
    t = raw(679); i = t.find('堪輿部名流列傳', 300)
    return t[:i], t[i:]

P665a, P665b = split_665()
P680a, P680b, P680c, P680d, P680e = split_680()
P679a, P679b = split_679()
SPECIAL = {'665a': P665a, '665b': P665b, '679a': P679a, '679b': P679b,
           '680a': P680a, '680b': P680b, '680c': P680c, '680d': P680d, '680e': P680e}

# 注意清代避諱：康熙帝名玄燁，殿本一律「玄」作「元」。
# 全语料「元武」49 次而「玄武」仅 1 次，「元空」同理。
# 检索必须带上避讳字形，否则会把「玄武最早见于明」这种假结论算出来（第一版就算错了）。
TERMS = ['乘生氣', '界水', '藏風', '得水', '元武|玄武', '朱雀', '明堂', '龍虎', '水口',
         '案山', '朝山', '穴病', '貫頂', '過山', '獨山', '擇向', '坐向',
         '平洋', '支幹', '幹龍', '五音', '福元', '遊年', '符鎮', '羅經', '分金',
         '元空|玄空', '三般卦', '二十四山', '上元', '三元', '納甲',
         '飛星', '挨星', '九運', '山星', '運星', '替卦', '兼向', '下卦', '城門']

def text_of(stratum):
    out = []
    for j, _ in STRATA[stratum]['juan']:
        out.append(SPECIAL[j] if isinstance(j, str) else raw(j))
    return '\n'.join(out)

if __name__ == '__main__':
    T = {k: text_of(k) for k in STRATA}
    sizes = {k: len(re.findall(r'[一-鿿]', v)) for k, v in T.items()}
    print('层的体量（正文汉字）')
    for k in STRATA: print(f"  {k:<18}{sizes[k]:>9,}   {STRATA[k]['desc']}")
    print()
    hdr = ''.join(f'{k.split()[0]:>7}' for k in STRATA)
    print(f"{'词':<8}{hdr}   最早出现层")
    for t in TERMS:
        pats = t.split('|')
        cnt = {k: sum(T[k].count(p) for p in pats) for k in STRATA}
        first = next((k for k in STRATA if cnt[k] > 0), None)
        row = ''.join(f'{cnt[k]:7d}' for k in STRATA)
        print(f'{t:<9}{row}   {first.split()[0] + " " + first.split()[1] if first else "—— 全语料 0 次"}')
