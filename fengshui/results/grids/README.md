# 实算格网

`.npy` 为 float32 二维数组，`*_meta.json` 给出 box、step、scale、lats、lons。

| 文件 | 范围 | 步长 | 尺度 |
|---|---|---|---|
| `luoyang_grid.npy` | 洛阳盆地 | 800 m | 1x |
| `luoyang3x_grid.npy` | 同上 | 800 m | **3x**（势 18 km / 形 6 km） |
| `luoyang3x_grid_smooth.npy` | 同上，分级前 4 km 平滑 | | |
| `luoyang3x_relief.npy` | 同上范围的地形起伏（对照用） | | |
| `guanzhong_grid.npy` | 关中渭河两岸 | 800 m | 3x，与洛阳同参数 |

读法：

```python
import numpy as np, json
G = np.load('luoyang3x_grid.npy')
M = json.load(open('luoyang3x_meta.json'))
lats, lons = np.array(M['lats']), np.array(M['lons'])
```

**注意**：洛阳 3x 给出 Kvamme 增益 +0.564（p=0.004），
关中用**完全相同的参数**给出 −1.400（p=0.954）。
两者矛盾，洛阳的正面结果已在 `rules_luantou.yaml` 中撤回。
保留这两个格网，是为了让后续的分层诊断（按朝代与遗址类型）能直接复用。
