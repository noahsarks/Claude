# 既有风水软件内部逻辑审计

目的：找到从业者实际在用的软件，读源码确认它们到底算什么，
再对照本项目的地形引擎，判断"地形层"是市场空白还是市场不要的东西。

日期：2026-09-02

---

## 一、找到了什么

### 商业闭源（只能看功能描述，不能读逻辑）
| 名称 | 平台 | 实际功能 |
|---|---|---|
| 袖裡乾坤·飛星風水 | Google Play | 玄空飞星排盘 + 罗盘 + 择日 |
| 简易玄空飞星 / 玄空风水App / 玄空飞星排盘App | 各安卓市场 | 同上 |
| fscalc.com / bazicode.com/en/flyingstar / prokerala | Web | Flying Star 排盘 |
| astrology-api.io/p/fengshui | API | Flying Stars / Kua / Tong Shu |

**全部是理气排盘器。** 没有一个碰地形。

### 开源可读（本次实际克隆并读了源码）
1. **`Sudo-Biao/suangua`** — 纯 Python，FastAPI + LLM 解读层。
   `core/fengshui/` 共 24 个模块、约 6000 行。
2. **`Horace-Maxwell/Horosa-Web-App...`** — Python 后端 + React 前端，
   `astrostudyui/src/components/fengshui/` 共 47 个文件、约 10900 行前端。
   README 自述"两类八派：户型图阳宅（纳气盘法/八卦阳宅法）；
   理气起盘罗盘（八宅大游年/玄空飞星/三合十二长生水法/金锁玉关/乾坤国宝/紫白飞星）"。

---

## 二、核心发现

### 发现 1：这些软件的"峦头"不是地形，是**话术层**

suangua 有个文件叫 `xuankong_luantou.py`（玄空峦头）。读完发现：
它**没有任何地形输入**。它读飞星盘，然后按星的旺衰输出建议文本：

```python
if _is_sheng(f_ws["level"]):
    advice.append(f"向星…当旺——此方宜见水（开阔、低平、路口、水池、动象），得水则旺财禄。")
else:
    advice.append(f"向星…已衰——此方忌见水动，宜静实（墙、柜、矮屏）…")
```

"此方宜见水"是一句**祈使句**，不是"此方有没有水"的判定。
软件从不知道那里有没有水。整个模块是 if-else 拼字符串。

Horosa 的 `xingshi.js`（形势派·龙穴砂水向五诀）更彻底：

```javascript
export function xingshi(sel = {}) {
  const longScore = (s.longSheng ? 2 : (s.longSheng === false ? -2 : 0))
    + (star ? (star.jx === 'good' ? 2 : star.jx === 'bad' ? -2 : 0) : 0)
    + (s.boHuan ? 1 : 0) + (s.guoXiaGood ? 1 : 0);
  …
}
```

`sel` 全部是**人工勾选项**：龙是否生、属九星哪一星、穴形、砂、水城、向。
它背后挂着 167 条古籍枚举（`fengshuiXingshiData.js`：定穴十三法、
证穴十三法、明堂吉九凶九、龙虎断十五、水口五煞三关、朝案、鬼乐官曜…），
是我见过最完整的峦头知识结构化。

**但软件的贡献只有加减法。** 感知（认出哪是龙、哪是穴、哪是砂）全由人完成，
软件做记账和评级（≥7 上吉、≥3 可用、≥-1 存疑、否则不宜）。

> **这一条直接对上本项目**：现存最好的峦头实现，把峦头当作**结构化判断表单**，
> 而不是计算。我们试图自动化的正是它交还给人的那一步——地形感知。
> 而我们自己的测量显示，那一步的自动化信噪比约 1:1（效应 +0.043，
> 1 km 位移噪声 0.042）。两边从相反方向指向同一结论。

### 发现 2：户型图功能里，没有任何图像识别

Horosa 的"上传户型图"只是把图片当画布背景。用户**手工**：设正北 → 用 16 类点标记
（入户门/窗/阳台/灶台/沙发/床/书桌/神龛/宠物床 = 气类；
水槽/洗手池/马桶/下水管/洗衣机/卫生间 = 水类）在图上打点 → 可选画轮廓多边形。

之后 `neijuGeometry.js`（室内凶局几何检测）跑规则，全部是初等几何：

```javascript
function facing(a, b, diag, tolDeg = 15, maxRatio = 1) {
  const off = Math.min(ang, Math.abs(ang - 90), Math.abs(ang - 180));
  return { ok: off <= tolDeg && dist <= diag * maxRatio, … };
}
```

开门见灶 = 门与灶连线偏角 ≤15° 且距离 ≤0.9 对角线。
穿堂 = 门与窗/阳台偏角 ≤12° 且距离 ≥0.6 对角线。
宅形狭长 = 长宽比 ≥2.5。缺角 = 该宫 12×12 采样点中过半落在轮廓外。

**规则本身约 200 行，是整个功能里最简单的部分。**
难的是从图纸得到那些点，而最好的开源实现直接放弃了自动解析。

这个模块的认识论值得抄。它开头写：

> ① 只对有充分输入的项给判定，缺相应标记者一律不判，
> 并如实列出「缺什么标记」，绝不用「没检测到」冒充「没有此凶局」。
> ② 判定是建议，人工勾选优先。③ 每条给证据（坐标、距离、偏角、比值）。

它的输出里 `skipped` 常比 `hits` 长——横梁压顶、开门见镜、房间形状、
厨房地面标高，全部老实列为"标记体系暂无此类"。

### 发现 3：suangua 的玄空排盘算错了，错在挨星顺逆

这是可判定的对错，不是流派差异。

标准挨星诀（《沈氏玄空学》）：山盘入中之星 = 运盘在坐山宫之星 X；
**顺逆由「X 所属卦中、与坐山同元龙（天/地/人）之山」的阴阳决定**。

suangua 用的是**坐山自己的阴阳**：

```python
mtn_direction = "yang" if mtn["yin_yang"] == "阳" else "yin"
mountain_chart = fly_stars(sitting_palace_yun_star, mtn_direction)
```

它的二十四山阴阳表是对的（壬甲丙庚乾坤艮巽寅申巳亥为阳，其余为阴），
错的是把这张表用在了错的山上。

Horosa 用的是对的（`liqiCore.js`）：

```javascript
const fx = (Vx === 5) ? (yyXiang === +1) : (GONG_YUAN[`${Vx}|${yXiang}`][1] === +1);
```

`GONG_YUAN[运星宫|向首元龙]` —— 正是"入中本宫取同元龙之山定阴阳"。

**跑了 9 运 × 24 坐山 = 216 局的三方对照**（`audit/three_way.py`）：

```
Horosa  与沈氏标准一致：216/216 = 100.0%
suangua 与沈氏标准一致： 60/216 =  27.8%
```

八运四大格局对照（八运 2004–2023，最常被查的一运）：

| | 旺山旺向 |
|---|---|
| 沈氏标准 | 丑、巽、巳、未、乾、亥（6 山） |
| Horosa | 同上（6 山） |
| suangua | 丁、丑、乙、午、卯、子、戌、未、癸、辛、辰、酉（**12 山**） |

标准答案 6 个，suangua 给出 12 个——旺山旺向按定义是稀缺格局，
给出一半坐山都是上吉，本身即不可能。
其中"子山午向"是教科书例题，标准答案**双星到向**，suangua 报**旺山旺向**。

复现：`python3 audit/three_way.py`（需先克隆 suangua）。

### 发现 4：评分权重全是手拍的，没人做过校准

Horosa 的纳气评分：

```javascript
export const HARM_MAP = {
  'break-wind':  { score: -15 }, 'break-water': { score: -15 },
  'double-bath': { score: -12 },
};
export function scoreNaqi({ windOk, waterOk, harms, dragonTiger }) {
  let s = 100;
  harms.forEach(h => { s += h.score; });
  s += Math.min(windOk + waterOk, 10);
  if (dragonTiger) s += (dragonTiger.level - 3) * 2;
  return Math.max(0, Math.min(100, Math.round(s)));
}
```

`-15`、`-12`、`(level-3)*2`、封顶 `10` 全无出处。
注释只写"锚点：一处破水 + 充足在位物 ≈ 95 分"——即锚在想要的输出上，
不是锚在任何证据上。Horosa 的形势评分（+2/-2/+1，阈值 7/3/-1）同理。

我们的引擎也是手拍权重。**区别只在于我们把它拿去和考古基准对撞过，
并且报告了它没通过。** 全行业没有第二份这样的测量。

---

## 三、对本项目的结论

1. **地形层确实是空白。** 读了两个最完整的开源实现 + 一圈商业产品，
   没有一个接入 DEM。理气排盘器已经饱和（且部分算错），
   峦头一律做成人工勾选表单。

2. **但空白的原因不明。** 前一轮民族志已经指出，城市从业者的利润在法器和室内咨询，
   不在选址；阴宅业务被普遍回避。空白可能是"没人做到"，
   也可能是"做了没人买"。这两个假设，读软件源码区分不了。

3. **可以确定要抄的：Horosa 的 `neijuDetect` 三层诚实防线。**
   "未检出 ≠ 无此凶局"、逐条给证据（坐标/距离/偏角/比值）、
   缺输入就列缺什么。我们的引擎输出一个 0–1 分，做不到逐条复核。

4. **户型图功能的成本重估。** 风水规则约 200 行初等几何；
   真正的工作量是"从 PNG 得到门/灶/床/厕的坐标"，而最好的开源实现放弃了它。
   我们若做自动解析，那是纯 CV 工程，与风水知识无关，
   且失败模式（认错一个马桶）会静默污染下游全部判定。
   起步应照抄 Horosa：手工打点，把 CV 当后续增量。

5. **理气不要自己写。** 216 局对照说明，一个看起来完整、有大量单元测试的实现
   仍可能 72% 的格局判错。若要理气，移植 Horosa 的 `liqiCore.flyChart`
   （已验证 216/216），并把这张 216 局表作为回归基准。

---

## 四、留存文件

- `audit/xk_diff.py` —— 标准挨星 vs suangua，216 局差异表
- `audit/three_way.py` —— 标准 / suangua / Horosa 三方对照

两者都需要本地克隆：
```
git clone --depth 1 https://github.com/Sudo-Biao/suangua
git clone --depth 1 https://github.com/Horace-Maxwell/horosa-web-app-comprehensively-improved-windows
```
