# -*- coding: utf-8 -*-
"""第三层 · DEM 地形：跑本项目的峦头引擎，并连同它自己的噪声一起报。
   结论前置：城市案例里地形不参与判断（A04/C01），此层只用于说明「不适用」有多不适用。"""
import sys, json, math, numpy as np
sys.path.insert(0,'/home/user/fs')
import luantou as L, kvamme as K
SITES=[('上海中心大厦',31.23559,121.50127,range(31,32),range(121,122)),
       ('金茂大厦',    31.23726,121.50139,range(31,32),range(121,122)),
       ('台北101',     25.03395,121.56461,range(25,26),range(121,122))]
EFFECT=0.043; NOISE_1KM=0.042; BG_SD=0.120     # results/final.json 与 noise_v4.json 实测
print(f"{'点':<14}{'高程m':>7}{'得分':>7}{'玄武':>6}{'护龙':>6}{'明堂':>6}{'得水':>6}{'水口':>6}{'藏风':>6}")
out={}
for n,la,lo,rows,cols in SITES:
    reg=K.Mosaic(n,rows,cols)
    m=L.metrics(reg,la,lo)
    s=L.score(m)
    h=float(np.atleast_1d(reg.sample(np.array([la]),np.array([lo])))[0])
    c=s['components']
    out[n]=dict(elev=h, final=s['final'], **{k:round(v,3) for k,v in c.items()})
    print(f"{n:<14}{h:7.1f}{s['final']:7.3f}"
          f"{c.get('xuanwu',0):6.2f}{c.get('hulong',0):6.2f}{c.get('mingtang',0):6.2f}"
          f"{c.get('water',0):6.2f}{c.get('water_gate',0):6.2f}{c.get('zangfeng',0):6.2f}")
print(f"\n本引擎自测的噪声底：效应量 {EFFECT:+.3f}，1 km 位移噪声 {NOISE_1KM:.3f}，背景 SD {BG_SD:.3f}")
print("即信噪比约 1:1。上表三个分数之间的差，全部落在噪声里，不可解读。")
json.dump(out, open('dem.json','w'), ensure_ascii=False, indent=1)
