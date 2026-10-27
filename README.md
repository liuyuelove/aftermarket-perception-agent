# aftermarket-perception-agent

> 用一句话驱动一条视觉算法迭代流水线：下载数据 → 抽帧 → 预标注 → 人在回路确认 →
> 训练 → 评估 → 模型转换，全程可中断、可恢复。

基于 [LangGraph](https://github.com/langchain-ai/langgraph) 的多智能体编排：主图理解意图并路由，
子图执行具体步骤，关键节点用 `interrupt()` 挂起等人确认。路由由 LLM 决定，但合法目标由代码白名单守住。

## 它解决什么问题

视觉算法的迭代不是一条直线：取数、清洗、标注、训练、评估、转模型，每一步都可能是不同脚本、
不同环境、不同人的活。串成 shell 脚本能跑通一次，但中间任何一步失败就得从头来，
需要人工介入的环节（比如标注）更是完全卡住。

这个项目把这些步骤建模成一张图：

- **状态可恢复** —— LangGraph 的 checkpoint 让流程挂在任意节点，重启后从断点继续
- **人工介入是一等公民** —— `interrupt()` 挂起而不是轮询等文件出现
- **每步可降级** —— LLM 后端、数据服务、预标注服务缺失时自动退回可用路径，不阻塞链路
- **路由与执行分离** —— 主图只决定「下一步去哪」，子图只负责「把这件事做完」

## 架构

```
node_task_proc_assistant        ← LLM 解析：任务名/类型/是否下载/是否标注/去哪
   ├─ next_node=node_end        → node_end → END
   ├─ 普通对话                   → END
   └─ next_node=node_task_proc  → node_task_proc_prepare（注入 thread_id/user_id）
                                      ↓
                                  node_task_classify   ← 校验任务名，查注册表
                                      ├─ 要下载 → node_data_download ─┬─ 要标注 → node_data_labeling
                                      │                                └─ 不标注 → node_func_proc
                                      └─ 不下载 → node_func_proc
                                      ↓
                                  node_func_proc（train / eval / model_cvt）
                                      ↓
                                  node_result_display → END
```

跳转几乎全靠 `Command(goto=...)` 在运行时决定，唯一的静态边是「子图跑完去汇总结果」。

## 快速开始

```bash
bash scripts/bootstrap.sh          # 建 .venv + 装依赖 + 自检，幂等
source .venv/bin/activate

# 填 LLM key（不填则回退到本地 Ollama）：编辑 .env 里的 DEEPSEEK_API_KEY
langgraph dev
```

浏览器打开 Studio，选 `agent` 图，能看到 5 个节点。发一句：

```
DMS2.0-人头-易甲文-NT98323-测试，做评估，不用下载数据
```

不想开 Studio 也可以直接命令行对话（人在回路会就地提示 y/n）：

```bash
python scripts/run_demo.py
```

## 核心设计

### 1. 路由交给 LLM，但边界由代码守住

模型输出 `next_node` 之后不直接当 `goto` 用，而是先过 `ALLOWED_NEXT_NODES` 白名单
（`graph/prompts.py`）。模型胡写一个不存在的节点名，图不会崩，而是兜底到 `node_end`。

### 2. 人在回路用 `interrupt()`，不是轮询

`node_data_labeling` 优先调 VLM 预标注；不可用或失败时 `interrupt()` 挂起，
前端弹出确认面板，提示把标注文件放进 `ai_data/images_with_label/`，点「确认继续」后
同一个节点会被**重新执行**（LangGraph 的固有语义），检查目录非空才继续。

想稳定复现这个交互，用这条（不需要任何外部服务）：

```
DMS2.0-人头-易甲文-NT98323-测试，做训练，需要标注，不用下载数据
```

### 3. 三个后端、两个降级点

LLM 按 `DeepSeek → OpenAI 兼容端点 → 本地 Ollama` 三级回退，占位符
（`your` / `xxx` / `sk-xxx` 之类）会被识别为「没填」，不会拿去做请求。

数据侧有两个降级点：没配 `DATA_SERVER_URL` 就复用本地已有数据；没配
`PREANNOTATION_SERVER_URL` 就跳过预标注直接进人在回路。

### 4. 本地数据复用必须比对任务名

只看「`ftp_data` 目录里有文件」就当成当前任务的数据，会让 A 任务悄悄用 B 任务的数据训练。
所以复用前先按任务名比对：不匹配时默认警告继续，`DATA_REUSE_STRICT=1` 时直接拒绝。

## 配置

`.env`（从 `.env.example` 复制）里只有几件事值得关心：

| 变量 | 作用 |
|---|---|
| `DEEPSEEK_API_KEY` | 填了就优先用 DeepSeek（`deepseek-chat`） |
| `LLM_BASE_URL` / `LLM_MODEL` | 自建 vLLM / 网关时填，DeepSeek 为空才生效 |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 前两者都空时的兜底，默认 `localhost:11434` |
| `RUNNER` | `local` 本机跑；`docker` 进容器跑（需要 GPU） |
| `DATA_SERVER_URL` | 不填 → 复用 `ai_data/ftp_data` 里已有数据（会先比对任务名） |
| `DATA_REUSE_STRICT` | `1` = 本地数据和任务名对不上就拒绝，`0` = 只警告（默认） |
| `PREANNOTATION_SERVER_URL` | 不填 → 跳过预标注，直接进人在回路 |

`.env` 由 `config/env.py` 在导入时统一载入（不覆盖已有的真实环境变量），
所以 `langgraph dev`、`scripts/run_demo.py`、pytest 三种入口行为一致。

## 测试

```bash
.venv/bin/python -m pytest tests -q --basetemp=.pytest_tmp
```

46 条用例，约 2 秒，**不需要 LLM / GPU / 真实算法工程**。

| 文件 | 覆盖 |
|---|---|
| `test_tasks.py` | 任务注册表：查找、大小写、validate 缺口 |
| `test_routing.py` | 子图路由：分类 → 下载 / 标注 / 训练的分支决策 |
| `test_training_split.py` | 训练集划分：确定性、比例、越界 |
| `test_human_interrupt.py` | 人在回路：请求构造、响应解析、消息不重复 |
| `test_graph_shape.py` | 图拓扑：节点齐不齐、子图是不是挂载态、Command 边 |
| `test_dataset.py` | 数据复用：文件名匹配、严格模式拒绝对不上 |
| `test_env.py` | `.env` 加载：不覆盖已有变量 |

## 目录结构

```
main.py                  入口：日志 / 目录 / 配置自检，导出 app
langgraph.json           langgraph dev 的加载配置（graphs.agent → main.py:app）

config/                  配置层：只读环境，不碰业务
  env.py                 环境变量 + 路径的单一来源
  llm.py                 LLM 后端选择（DeepSeek → OpenAI 兼容 → Ollama）
  tasks.py               任务注册表（任务类型 × 功能 → 工程名 / 数据路径 / 流水线）
  context.py             从 config 提取 thread_id / user_id

graph/                   图定义：只描述拓扑，不放业务
  state.py               主图与子图共享的 State、结构化输出契约
  prompts.py             assistant 系统提示词 + 路由白名单
  task_proc_graph.py     子图组装（5 个节点）
  main_graph.py          主图组装 + 编译

nodes/                   节点：只做「读 state → 调服务 → 返回 Command」
  assistant.py           理解意图，输出结构化决策
  prepare.py             注入 thread_id / user_id
  result_display.py      把执行结果交回助手总结
  end.py                 收尾
  task_proc/             子图节点：classify / download / labeling / train_data_gen / func_proc

services/                服务层：可被单独测试，不依赖图
  dataset.py             下载 → 解压 → 抽帧
  annotation.py          VLM 预标注（不可用则降级）
  training.py            train / eval / model_cvt 调度
  human_interrupt.py     人在回路的请求构造与解析
  prj_run.sh             local / docker 两种执行器

tools/                   底层工具：图像、XML、日志解析、HTTP 客户端（算法无关）
fcos/                    算法工程（真实代码放这里）；fcos/_mock 是演示替身

tests/                   46 个用例
scripts/                 命令行对话 + 一键 bootstrap
openapi.json             LangGraph 平台 API 快照，仅作参考，运行时不读
```

依赖方向单向向下：`main → graph → nodes → services → tools`。
`tools` 不认识 `config`，`services` 不认识 `nodes`。

## 已知边界

- `fcos/` 里只有 mock 工程，train/eval 走替身，不跑真实模型。放真实代码进去 mock 自动失效，
  不用改配置 —— `services/training.py` 找工程目录时**真实工程优先**。
- 任务注册表里部分条目缺工程名或数据路径，启动时打 warning，跑到对应任务会给出可读错误
  而不是 `KeyError`。
- `docker` 执行器需要 GPU 和对应镜像，本机默认走 `local`。

## License

私有项目，未授权请勿分发。
