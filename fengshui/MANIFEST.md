# 仓库清单 · 文献、数据、脚本、结论

**这份文件是全仓库的索引与出处台账。** 每一项都注明：是什么、从哪来、什么许可、能不能重跑。

最后更新：2026-09-03。分支 `claude/xuanxue-analysis-jw7nh7`。

---

## 一、目录总览

```
fengshui/
├── MANIFEST.md              ← 本文件
├── README.md                M0 阶段说明（引擎的规则出处与双尺度设计）
├── rules_luantou.yaml       规则登记册 v0.15，26 个顶层节，含全部结论与撤回记录
├── luantou.py               引擎主体（v0.6）
├── luantou_v1.py            v0.1 存档
├── luantou_v3.py            v0.3 存档
├── requirements.txt
├── scripts/                 25 个分析脚本
├── results/                 结果 JSON / PNG / 日志
│   ├── round2/              三区分层抽样的背景与正样本
│   └── grids/               实际算出的格网 .npy 与元数据
├── sources/                 抓取过程留下的索引文件
├── audit/                   既有软件反编译审计
│   ├── existing_software.md
│   ├── xk_diff.py / three_way.py
│   └── geo/                 商业软件地理逻辑审计 + 三引擎对比
└── masters/                 风水师名录与案例拆解
    ├── roster.yaml          34 人（1826-2026）
    ├── analysis.md          三轮拆解统计与结论
    ├── cases/               16 个案例文件 + index.yaml
    └── corpus/              原始语料（公有领域）
        ├── gjtsjc/          古今圖書集成·堪輿部 651-680 卷（30 卷，约 42 万字）
        ├── shen/            沈氏玄空学连载 68 篇（约 34 万字）
        └── fetch/           抓取脚本
```

---

## 二、原始语料（全部公有领域，已入库）

| 语料 | 位置 | 体量 | 出处 | 许可 |
|---|---|---|---|---|
| **《欽定古今圖書集成·博物彙編·藝術典·堪輿部》第 651–680 卷** | `masters/corpus/gjtsjc/` | 30 文件，约 42 万字 | zh.wikisource.org，底本 1700–1725 殿本 DjVu 校对文本 | 页面自带声明：作者逝世逾百年且 1931 前出版，全球公有领域 |
| **《沈氏玄空学》连载** | `masters/corpus/shen/` | 68 文件，约 34 万字 | 新浪博客「山水清澈」2017 逐条转录本 | 章仲山（清嘉道）、沈竹礽（1849–1906）、王则先（民国）均逝世逾五十年 |

### 派生文件

| 文件 | 内容 |
|---|---|
| `corpus/bios679.json` | 114 位堪輿家传记，结构化 `{name, text}` |
| `corpus/jishi.txt` | 堪輿部紀事 8.4 千字，案例出自《後漢書》《魏志》《晉書》《陳書》《唐書》《宋史》等 |
| `corpus/yiwen.txt` | 堪輿部藝文 1.86 万字，**历代批判文献**（嵇康、呂才、趙汸、胡翰、羅虞臣、項喬） |
| `corpus/zalu.txt` | 堪輿部雜錄 3.5 千字 |
| `corpus/yinzhai_parsed.json` | 《阴宅秘断》解析出的 21 案，含坐向、元运、正文 |
| `corpus/shen/INDEX.md` | 68 篇连载的篇题索引 |

### 语料里最要紧的四段

1. **卷 679 名流列傳** —— 秦至明 114 位堪輿家。含廖均卿（1409 选天壽山即明十三陵）、
   駱用卿（择永陵，**候选十八处**）、徐仁旺与吳景鸞（**牛頭山前地 vs 後地之争**）。
2. **卷 680 紀事** —— 正史所载案例。含管輅论毋丘儉墓「元武藏頭，蒼龍無足，白虎銜尸，
   朱雀悲哭，四危以備，法當滅族」，以及郭璞「葬龍角/葬龍耳」。
3. **卷 680 藝文** —— 整卷是反对与质疑的文章，且收入钦定官修类书。
   其中呂才《五行祿命葬書論》（约 640）用《春秋》记录做基率检验，方法与本项目同类。
4. **《宅斷》阳宅十七条 + 阴宅五十四条** —— 逐案记录体：
   坐向（含兼线）+ 元运 + 形势 + 断语 + 应验 + 三家按语。

---

## 三、读过但**不入库**的文献（版权原因）

以下是本项目实际依据的材料，但属他人著作权范围，仓库只登记出处与获取方式，**不复制正文**。
案例文件中的引用为研究性节引。

| 文献 | 用途 | 获取方式 |
|---|---|---|
| **Ren, Youcao. *Feng Shui: Changing Rules and Meanings*. PhD thesis, Univ. of Sheffield** | `masters/cases/A01–A04` 全部 A 级民族志案例的唯一来源。第 5 章为 2014–2017 浙江武义/金华、杭州、河南的一手田野 | White Rose eTheses 开放获取，322 页。搜索标题即得 |
| **Verhagen, P. (CAA 2007) 关于考古预测建模的演绎 vs 归纳** | 推翻了「归纳拟合权重」的最初方案 | 会议论文集，开放 |
| **Magli, G. arXiv:1804.00264** | 帝陵朝向的天文考古分析 | arXiv 开放 |
| **无定河流域史前聚落论文** | 提供 `rules_luantou.yaml` 的 `empirical_basis` 数字 | 期刊 |
| **王其亨等《风水理论研究》** | 明清皇陵测绘；`rules_luantou.yaml` 的 `historical_note` 引其「平格图」一段 | 天津大学出版社 |
| **Feuchtwang, *An Anthropological Analysis of Chinese Geomancy* (1974)** | **尚未读。** 架构重构前应先读 | 图书 |
| **fscalc.com 生产 JS 包（734 KB）** | 商业软件地理逻辑反编译 | 不入库。研究性节引存 `audit/geo/fscalc_extract.js`（9 KB） |
| **Sudo-Biao/suangua、Horace-Maxwell/Horosa** | 开源引擎审计 | 不入库。克隆命令记于 `audit/existing_software.md` |

---

## 四、数据

| 文件 | 内容 | 来源 |
|---|---|---|
| `results/round2/guobao.json` | 4356 处全国重点文物保护单位坐标 | Wikidata SPARQL，`P1435 = Q1188574`。CC0 |
| `results/round2/{bg,pos}_*.json` | 京津冀、晋南豫北、关中三区的背景点与正样本点及其得分 | 本项目计算 |
| `results/grids/*.npy` + `*_meta.json` | 洛阳、洛阳 3x、关中的实算格网 | 本项目计算 |
| `audit/geo/decl.json` | 八城市的 NOAA WMM-2025 磁偏角实测值（2026-09） | NOAA `calculateDeclination` API |
| DEM | **不入库**（780 MB）。Copernicus DEM GLO-30，`s3://copernicus-dem-30m`，`--no-sign-request` | 重下脚本 `scripts/fetch_dem.sh` |

---

## 五、可复现的检验（脚本 + 结果）

| 检验 | 脚本 | 结果 | 结论 |
|---|---|---|---|
| 挨星实现三方对照（216 局） | `audit/three_way.py` | — | Horosa 216/216、fscalc 216/216、suangua **60/216 = 27.8%** |
| 商业软件地理逻辑 | `audit/geo/decl.py` `pipeline.py` `attribute.py` | `audit/geo/README.md` | 不做磁偏角校正在哈尔滨会让 **76%** 的读数落到错的山上 |
| **跨两百年挨星回归** | `masters/corpus/regress_qing.py` | 见 `cases/B01` | 与章仲山原案**下卦 6/6 一致** |
| **语料内部一致性** | `masters/corpus/consistency_test.py` | 见 `cases/B02` | 上山下水断语必负 7/7；旺山旺向只有一半正 2/4；rho=+0.460 p=0.036 |
| Kvamme 增益（五点验证） | `scripts/validate.py` | `results/validation.json` | 5 点中仅 1 点通过 |
| 分层抽样（三区） | `scripts/final_run.py` | `results/final.json` | 效应 +0.043，背景 SD 0.120 |
| 位移噪声 | `scripts/noise_v4.py` | `results/noise_v4.json` | 1 km 位移噪声 0.042 ≈ 效应量，**信噪比 1:1** |
| 天花板（±100 m） | `scripts/ceiling.py` | `results/ceiling.json` | SD 0.024 = 效应的 57%，是真地形异质性 |
| 洛阳全城格网 | `scripts/luoyang3x.py` + `_report.py` | `results/luoyang3x_report.json` | 增益 +0.564，p=0.004 |
| 关中复核（同参数） | `scripts/guanzhong.py` + `_report.py` | `results/guanzhong_report.json` | 增益 **−1.400**，p=0.954 —— 与洛阳矛盾 |

---

## 六、结论台账（全部登记在 `rules_luantou.yaml`）

`rules_luantou.yaml` 是本项目的**唯一结论出口**，26 个顶层节，含每一次撤回。

### 已撤回的结论（各带证据）

- 归纳拟合权重的方案 —— Verhagen：演绎优先，才能让考古数据留作独立检验
- 「+0.467」尺度扫描结果 —— 被我自己引入的边缘裁剪造成的选择效应抬高
- 把平滑排在坐标工作之前的优先级 —— 三次独立降噪尝试全部失败
- **洛阳 +0.564 作为预测效度的证据** —— 关中同参数给出 −1.400

### 当前成立的结论

1. **信噪比约 1:1**（效应 +0.043，1 km 位移噪声 0.042）。这是全行业唯一一份这样的测量。
2. **地形分析只在阴宅是核心业务**，而阴宅正是当代城市从业者集体回避的一块（四次独立确认）。
3. **坐向来自生辰，不来自地形**（四案一致、零案反例）。引擎须改为坐向必填输入。
4. **产品应输出带理由的候选清单，不是一个分数**（吴莲 2010s + 駱用卿十八道 1520s，相隔五百年）。
5. **凶格是门槛式的，不是加权求和**（管輅「四危以備」）。
6. **正样本标签是几套择址范式的混合物**（A05 + A10 + A06 三重确认）——
   这可能才是洛阳/关中矛盾的真正原因，而非模型不稳。
7. **挨星实现正确性已解决**：四端点互证（沈氏表 ↔ fscalc ↔ Horosa ↔ 章仲山原案）。
8. **按案例集自己的记录，理气不足以解释结果，余量全记在形势上** ——
   本项目唯一一个从传统内部支持地形层的论证。
9. **判据与坐标在历史文献里几乎从不同时出现** —— 这是历史验证路线的天花板，
   不取决于还能找到多少材料。
10. **新增指标 `ridge_layers`**（视线方向穿越山脊次数）—— 来自唯一一次术者对地形的计数，尚未实现。

---

## 七、没做到的、以及为什么

| 事项 | 状态 | 阻塞点 |
|---|---|---|
| 商业 APK 反编译 | **未做成** | apkcombo 能取下载链但一律 302 至 pureapk/apkpure，Cloudflare 对机房 IP 全部 403；无头 Chromium 走会话代理时全站连接重置（未加载代理 CA，按规不能关 TLS 校验）。jadx 1.5.1 已备好 |
| 谈养吾《大玄空实验》原文 | **未取得** | 1930s 出版，作者 1970s 卒，可能仍在版权期；未找到开放全文 |
| 《阴宅秘断》完整 54 条 | **取到 21 案** | 转录本本身只到图五十二 |
| 把清代案例落到坐标 | **不可能（按现有材料）** | 21 案中仅 3 案有村/桥级地名。唯一缝隙是「无锡石塘湾孙姓祖墓」，需地方志或田野 |
| 读 Feuchtwang (1974) | **未读** | 架构重构前应先读 |

---

## 八、怎么重跑

```bash
pip install -r requirements.txt
bash scripts/fetch_dem.sh                  # 下 DEM（780 MB，AWS 开放数据）

python3 audit/three_way.py                 # 挨星三方对照（需先克隆 suangua）
python3 audit/geo/decl.py                  # 拉 NOAA 磁偏角实测
python3 audit/geo/attribute.py             # 三引擎分歧归因
python3 masters/corpus/regress_qing.py     # 跨两百年挨星回归
python3 masters/corpus/consistency_test.py # 语料内部一致性

python3 masters/corpus/fetch/grab_gjtsjc.py  # 重抓古今圖書集成堪輿部
python3 masters/corpus/fetch/walk.py         # 重抓沈氏玄空学连载（向前）
python3 masters/corpus/fetch/walkfwd.py      # 同上（向后）
```

抓维基文库须自定 User-Agent 并留 2 秒间隔（通用 UA 会被限流）。
