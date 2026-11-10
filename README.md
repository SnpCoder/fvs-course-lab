# fvs-course-lab — SSD 过滤向量检索课程实验

本仓库是《计算机系统设计》课程实验的个人优化实现与复现材料。课程原版
PipeANN-Filter、GateANN、数据集和预构建索引不在此仓库中。

## 实验报告

- [实验报告 PDF](report/实验报告.pdf)

报告包含实验环境、Debug 验证、30 行正式实验、两张核心图、机制分析、
优化设计与验证计划，以及本次自主探索的实现说明。

## 优化实现

优化目标：GateANN 在强过滤（Low Selectivity）下候选池被无效节点占满，
增大 L 只能增加 tunneling 步数。实现把“找有效候选”和“沿图扩展”分开：
对单标签、小 posting 的稀有标签，直接从标签倒排生成候选，按 PQ 距离取
前 `L_seed` 个，再走 GateANN 原有的 4 KiB 读页和精确 L2 重排。

改动共 5 个文件，+294/−28：

- `gateann/include/utils/spmat_filter_store.h`：标签到节点的倒排表
  `build_inverted()` / `posting()`；
- `gateann/include/ssd_index.h`：`pipe_search` 的可选 `seed_ids` 参数；
- `gateann/src/search/pipe_search.cpp`：seed 候选、PQ top-L_seed、
  `GATEANN_SEED_ONLY` 精确重排，以及 valid-frontier BFS 对照；
- `gateann/tests/search_disk_index_yfcc.cpp`：单标签路由、阈值回退和
  `TUNNELSTATS` 诊断；
- `gateann/include/utils/percentile_stats.h`：seed/tunnel 计数。

完整 diff 见 [patches/0001-explore-rare-label-seeding.patch](patches/0001-explore-rare-label-seeding.patch)。
课程 AIO 兼容补丁见 [patches/gateann_aio_compat.patch](patches/gateann_aio_compat.patch)。

## 主要结果

Low 档，3 轮 × 200 条查询的中位数：

| 方案 | Recall@10 | 平均时延 | 逻辑 I/O |
|---|---:|---:|---:|
| GateANN 原版 L=320 | 34.30% | 559.9 μs | 4.38 |
| seed-only L_seed=20 | 90.55% | 394.8 μs | 19.77 |
| **seed-only L_seed=40** | **97.20%** | **517.6 μs** | **39.24** |
| seed-only L_seed=80 | 98.15% | 744.6 μs | 76.19 |
| 种子 + 图扩展 | 35.90% | 724.6 μs | 6.53 |
| valid-frontier BFS H=2 | 94.90% | 5,050.5 μs | 78.95 |

结论：L_seed=40 是这份数据的拐点；继续加种子的收益很小，时延和 I/O
明显上升。只加种子、保留图扩展时 Recall 仍接近原版，说明图扩展会把
无效邻居重新填满候选池。Medium/High 的 posting 超过阈值，自动回退原
路径，Recall 与原版一致。

## 复现

1. 使用课程 GateANN 固定 commit `71e87cbf0e25c0400c0109dd25a64a7c4dccc9dd`。
2. 应用 `patches/gateann_aio_compat.patch`，再应用探索 patch；或直接把
   `gateann/` 下的 5 个修改文件覆盖到对应路径。
3. Release + AIO 构建 `search_disk_index_yfcc`。
4. 运行正式索引和 Formal workload，设置：

```bash
GATEANN_LABEL_SEEDS=1
GATEANN_SEED_ONLY=1
GATEANN_SEED_LIMIT=40
GATEANN_LABEL_SEED_MAX=10000
```

`scripts/` 下保留对照运行、汇总和绘图脚本；`results/` 下保留汇总 CSV。
数据集、预构建索引和原始运行日志不放入仓库。

## 说明

- 优化只覆盖单标签、posting ≤ 10,000 的稀有标签；多标签 posting 交集未实现。
- 时延使用系统 Query Phase 的 `mean_latency_us`；GateANN 只输出整数 QPS 时，
  适配器用 `1,000,000/QPS` 反推，报告在方法部分说明了这一限制。
- 课程原版系统与数据集的版权/许可归各自上游项目；本仓库只保存课程实验的
  个人改动和复现材料。
