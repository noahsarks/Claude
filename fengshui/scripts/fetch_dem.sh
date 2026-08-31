#!/bin/bash
# 下载复现本轮验证所需的 9 幅 Copernicus DEM GLO-30 瓦片（AWS 开放数据，免账号）
# 用法: bash fetch_dem.sh <目标目录>
set -e
OUT=${1:-./dem}; mkdir -p "$OUT"; cd "$OUT"
B=https://copernicus-dem-30m.s3.amazonaws.com
for t in N39_00_E115_00 N39_00_E116_00 N40_00_E115_00 N40_00_E116_00 \
         N34_00_E107_00 N34_00_E108_00 N34_00_E109_00 N39_00_E117_00 N40_00_E117_00; do
  n="Copernicus_DSM_COG_10_${t}_DEM"
  [ -s "$n.tif" ] && { echo "have $t"; continue; }
  echo "fetch $t"; curl -sS --max-time 900 -o "$n.tif" "$B/$n/$n.tif"
done
echo "done: $(ls -1 *.tif | wc -l) tiles"
