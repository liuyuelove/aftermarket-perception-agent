# fcos/_mock —— 演示用的假算法工程

这不是真实算法代码，只是**让图能从头跑到尾**的最小替身：没有 GPU、没有数据集、
没有真实 fcos 工程时，用它验证「路由 → 子图 → 结果汇总」这条链路是通的。

## 它是怎么被用上的

`services/training.py` 定位工程目录时按顺序找：

1. `fcos/<func_type>/<prj>/` —— 真实工程，存在就用它
2. `fcos/_mock/<func_type>/<prj>/` —— 上面不存在时的兜底，**会打 warning**

所以把真实 fcos 代码放进 `fcos/dms/...` 后，mock 自动失效，不用改配置。

## 当前覆盖范围

| 任务 | 工程 | train | eval | model_cvt |
|---|---|---|---|---|
| DMS2.0 / 人头 | `dms/dms_head_det` | ✅ 假 loss 曲线 + 假 checkpoint | ✅ 假检测框 + 结果目录 | ✅ 假转换 |

其它任务（安全带 / 人眼 / BSD / HOD …）没有 mock 工程，运行时会给出
「工程目录不存在」的可读错误 —— 这是刻意的：宁可明确报错，也不要伪造结果。

## 假结果的边界

- `eval.py` 不跑任何模型，它给每张图写一个**固定位置**的框（居中偏左上）
- `train.py` 打印的是写死的 loss 数字，不是真收敛
- 产物落在 `ai_results/model_eval_result/`，可以打开看，但**不要当成模型效果**

跑真实训练请把 `RUNNER` 设成 `docker`（需要 `--gpus all`），并把真实
fcos 工程放到 `fcos/<func_type>/<prj>/`。
