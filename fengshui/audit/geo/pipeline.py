# -*- coding: utf-8 -*-
"""同一位置 + 同一罗盘读数 → 三个引擎各自算出什么。
   链条：磁读数 --(磁偏角)--> 真方位角 --(24山界)--> 坐山 --(挨星)--> 格局
   三处都会分歧，逐段量化。"""
import json, math

# ── 24 山：名, 中心度, 宫(洛书), 元龙序(1地2天3人), 阴阳(+1阳) ──
SHAN = [
 ('壬',345,1,1,+1),('子',  0,1,2,-1),('癸', 15,1,3,-1),
 ('丑', 30,8,1,-1),('艮', 45,8,2,+1),('寅', 60,8,3,+1),
 ('甲', 75,3,1,+1),('卯', 90,3,2,-1),('乙',105,3,3,-1),
 ('辰',120,4,1,-1),('巽',135,4,2,+1),('巳',150,4,3,+1),
 ('丙',165,9,1,+1),('午',180,9,2,-1),('丁',195,9,3,-1),
 ('未',210,2,1,-1),('坤',225,2,2,+1),('申',240,2,3,+1),
 ('庚',255,7,1,+1),('酉',270,7,2,-1),('辛',285,7,3,-1),
 ('戌',300,6,1,-1),('乾',315,6,2,+1),('亥',330,6,3,+1)]
BY_NAME = {s[0]: s for s in SHAN}
OPP_GONG = {1:9,9:1,2:8,8:2,3:7,7:3,4:6,6:4}
GONG_YUAN = {(s[2], s[3]): s for s in SHAN}

def mountain_of(deg):
    d = deg % 360
    for s in SHAN:
        lo, hi = (s[1] - 7.5) % 360, (s[1] + 7.5) % 360
        if (lo < hi and lo <= d < hi) or (lo > hi and (d >= lo or d < hi)):
            return s
    raise ValueError(deg)

def _idx(n): return (n - 5 + 9) % 9
def _val(c, n, fwd): return ((c-1+_idx(n)) % 9 + 1) if fwd else (((c-1-_idx(n)) % 9 + 9) % 9 + 1)

def chart(yun, zuo_name, rule):
    """rule: 'std' 沈氏标准 | 'fscalc' 奇偶式(等价标准, 五取本宫洛书) | 'suangua' 误用本山阴阳"""
    zuo = BY_NAME[zuo_name]
    gZ, yuan = zuo[2], zuo[3]
    xiang = GONG_YUAN[(OPP_GONG[gZ], yuan)]
    gX = xiang[2]
    yunp = {n: _val(yun, n, True) for n in range(1, 10)}
    def polarity(X, palace_gong, self_shan):
        if rule == 'suangua':
            return self_shan[4] == +1
        if X == 5:
            if rule == 'fscalc':                 # 五 → 取该宫本身的洛书数定奇偶
                X = palace_gong
            else:                                # Horosa/标准常用：五 → 从本山阴阳
                return self_shan[4] == +1
        if rule == 'fscalc':                     # 奇数卦(1,3,7,9): 地阳天阴人阴；偶数卦反之
            return (self_shan[3] == 1) if (X % 2 == 1) else (self_shan[3] != 1)
        return GONG_YUAN[(X, self_shan[3])][4] == +1
    Vs, Vx = yunp[gZ], yunp[gX]
    sp = {n: _val(Vs, n, polarity(Vs, gZ, zuo)) for n in range(1, 10)}
    xp = {n: _val(Vx, n, polarity(Vx, gX, xiang)) for n in range(1, 10)}
    ms, mf = sp[gZ] == yun, sp[gX] == yun
    fs, ff = xp[gZ] == yun, xp[gX] == yun
    ge = ('旺山旺向' if ms and ff else '上山下水' if mf and fs else
          '双星到向' if mf and ff else '双星到坐' if ms and fs else '其他')
    return dict(zuo=zuo_name, xiang=xiang[0], ge=ge, shan=sp, xiang_pan=xp, gZ=gZ, gX=gX)

# ── 三个引擎的地理步骤 ──
DECL = {r['name']: r for r in json.load(open('decl.json'))}

def true_bearing(engine, city, mag_reading):
    d = DECL[city]
    if engine == 'fscalc':   return mag_reading + d['noaa_east']   # WMM 东正，真=磁+偏
    if engine == 'horosa':   return mag_reading - d['horosa2013']  # 表西正，真=磁−西偏
    if engine == 'suangua':  return mag_reading                    # 不校正
    raise ValueError(engine)

RULE = {'fscalc': 'fscalc', 'horosa': 'std', 'suangua': 'suangua'}

def run(city, mag, yun=9):
    out = {}
    for eng in ('fscalc', 'horosa', 'suangua'):
        tb = true_bearing(eng, city, mag)
        # 罗盘读的是「向」，坐 = 向 + 180
        zuo = mountain_of(tb + 180)
        out[eng] = dict(true=round(tb % 360, 2), zuo=zuo[0],
                        ge=chart(yun, zuo[0], RULE[eng])['ge'])
    return out

if __name__ == '__main__':
    import sys
    print("九运（2024-2043）。罗盘读数 = 磁北向首度数。\n")
    for city, mag in [('杭州', 178.0), ('洛阳', 172.0), ('哈尔滨', 186.0), ('北京', 5.0)]:
        r = run(city, mag)
        print(f"── {city}  罗盘读 {mag}° ──")
        for eng in ('fscalc', 'horosa', 'suangua'):
            e = r[eng]
            print(f"   {eng:<8} 真方位 {e['true']:>6.2f}°  坐{e['zuo']}  → {e['ge']}")
        gs = {r[e]['ge'] for e in r}; zs = {r[e]['zuo'] for e in r}
        print(f"   坐山 {'一致' if len(zs)==1 else '不一致 '+ '/'.join(sorted(zs))}"
              f" ；格局 {'一致' if len(gs)==1 else '不一致 '+ '/'.join(sorted(gs))}\n")
