# A股市场主线识别 Agent

面向 A 股市场的结构分析智能分身，用户只需说"今日主线"即可获得完整的六段式市场分析报告。

## 功能

- 自动拉取三大指数行情、行业涨跌、个股行情、舆情等数据（通过财新数据平台）
- 基于涨停集中度 + 行业涨幅 + 周月趋势的四维综合评分识别主线
- 判断情绪周期（冰点/调整/修复/主升/高潮）
- 识别核心锚点个股（情绪标的/趋势中军/补涨标的）
- Agent LLM 亲自生成六段式交易报告

## 使用方式

### ✅ 规范指令（推荐使用，AI 稳定路由到本 Agent）

| 指令 | 说明 |
|---|---|
| `今日主线` | 分析最近一个交易日 |
| `主线识别 2026-06-17` | 指定日期分析 |
| `分析今天A股市场主线` | 完整描述 |
| `每日主线` | 同义词触发 |
| `调用主线分析agent` | 直接点名 |

**关键词**：指令中包含 **"主线"** 二字，AI 即可稳定识别意图并调用本 agent。

Agent 会自动：鉴权 → 拉取数据 → 结构化分析 → AI 生成六段式报告（约 5 分钟）。

### ❌ 容易误路由的指令（请避免使用）

以下指令会**触发其他 agent 或导致 AI 不知该调用谁**，**不要这样调用本 agent**：

| ❌ 模糊指令 | ⚠️ AI 可能误调用的对象 |
|---|---|
| `分析下今天市场` | Wind / 通用行情 agent |
| `看看大盘` | 行情查询 agent |
| `今天股票怎么样` | 个股分析 agent |
| `市场行情` | 通用行情接口 |
| `今天该不该买` | 投资建议类（无对应 agent，会乱答） |
| `分析下XX股票` | cxdata-stock-analysis-agent |
| `电子板块怎么样` | 板块分析 agent |

> 如果使用了上述模糊指令，AI 会主动反问澄清，但会多一次交互——建议直接用规范指令。

### 🔀 与其他 agent 的边界（避免重复调用）

| 用户需求 | 应调用 |
|---|---|
| **A股市场整体主线 / 板块强弱对比 / 情绪周期** | **本 agent**（主线识别） |
| 单只个股的基本面/财报/估值分析 | cxdata-stock-analysis-agent |
| 单一板块的深度分析（如只看电子） | 板块分析 agent |
| 单只股票的最新价 / K线 / 分钟行情 | Wind / 通用行情 agent |
| 港股 / 美股 / 期货 / 加密货币 | 对应市场 agent |
| 回测 / 选股 / 策略 | 策略类 agent |

## 前置依赖

1. 安装 Python 依赖：`pip install python-dotenv requests`
2. 首次使用需完成鉴权（**新版 SMS 验证码登录机制**）：
   - 调用 `skills/mainline-analysis/scripts/auth.py status` 检查认证状态
   - 未认证时按 AGENT.md 引导用户完成协议确认 + 手机号验证码登录
   - 认证信息持久化在 `~/.cxda-cache/.shared/cxda_auth.json`，**跨所有 cxdata Agent 共享**，无需重复认证
   - 数据源 Skill 已内置在 Agent 中，无需额外下载

## 目录结构

```
cxdata-mainline-analysis-agent/
├── AGENT.md                                       # Agent 整体人设与执行逻辑
├── SOUL.md                                        # 身份、性格、能力边界
├── rules.md                                       # 硬性规则
├── config.json                                    # 元数据配置
├── skills/
│   ├── mainline-analysis/                         # 主线识别分析 Skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── fetch_data.py                      # 数据获取（subprocess 调 query.py）
│   │       ├── analyze_data.py                    # 结构化分析（综合评分 + 情绪周期）
│   │       ├── generate_report.py                 # 输出结构化 prompt（供 Agent LLM 使用）
│   │       ├── auth.py / common.py /              # cxdata 官方鉴权四件套（拷自新版 skill）
│   │       ├── cxda_cache_cli.py / query.py
│   │       ├── requirements.txt
│   │       └── data/                              # 中间数据（自动生成，.gitignore 排除）
│   ├── cxdata-stock-market-information/           # 内置数据源（空壳：SKILL.md + references）
│   ├── cxdata-stock-basic-information/            # 内置数据源（空壳）
│   └── cxdata-public-opinion-stock-index/         # 内置数据源（空壳）
└── README.md
```

## 变更历史

### 2026-06-17 涨跌停口径改为交易所封板字段

- **问题**：旧逻辑用「涨幅 ≥ 阈值 × 0.99」近似判断涨停，因创业板/科创板涨停阈值是 20%、ST 折半等规则差异，导致统计数与行情软件不一致（旧：涨停 97 / 跌停 15；实际：涨停 98 / 跌停 21）
- **方案**：
  - **fetch_data.py** `is_limit_up` / `is_limit_down` 改为直接读接口字段 `PRICE_UPDOWN_TYPE_PAR == "涨停" / "跌停"`，删除 `_get_limit_threshold` 阈值计算逻辑
  - **analyze_data.py** 同步改为接口字段判定
- **效果**：统计口径与交易所/行情软件完全一致，不再因板块差异漏算或多算

### 2026-06-17 报告生成规则收紧（不暴露内部信息 + 强制免责声明）

- **问题**：生成的报告头部混入了积分消耗、接口调用次数等内部运行信息；末尾缺免责声明；AI 结论出现"操作建议观望 / 仓位控制在半仓以下"等变相买卖指令
- **方案**：
  - **AGENT.md** Step 4「⛔ 绝对禁止事项」新增第7条（禁止暴露积分/接口次数/API KEY/手机号等内部信息）和第8条（禁止买卖指令性措辞）；「✅ 你需要完成的分析」新增第7条（必带免责声明）
  - **AGENT.md** Step 5 补充报告必须结构 + 免责声明模板原文；报告头规则收紧为「仅标题，不要写总成交/涨停/跌停概览行，不得包含数据字段名、算法口径等内部实现细节」
  - 同步删除报告中的"涨跌停口径：使用接口 PRICE_UPDOWN_TYPE_PAR 字段"等实现细节标注

### 2026-06-17 新增 Agent 路由边界与用户使用指引

- **问题**：新设备测试时，AI 在用户指令模糊（如"分析下今天市场"）的情况下，会误调用 Wind / 通用行情 / 个股分析等其他 agent，导致主线分析 agent 失效
- **方案**（三层防御，覆盖 Claude Code 内调度与 OpenClaw 等中转平台调度两种场景）：
  - **AGENT.md** 顶部新增 Step 0「适用边界判定」：明确 ✅ 命中条件（含"主线/市场主线/今日主线"等关键词或点名 agent）/ ❌ 让出场景（个股分析、单一板块、其他市场、选股策略等路由表）/ ⚠️ 模糊指令强制反问（禁止自行路由到其他 agent，宁可多一次交互）
  - **SKILL.md** description 收紧为"仅处理 A股市场整体主线结构"，并在顶部加「适用边界（路由判断必读）」表，覆盖个股/单板块/其他市场等让出场景
  - **README.md** 使用方式段重写：✅ 规范指令表（关键词"主线"为稳定触发词）+ ❌ 误路由指令表（"看看大盘/分析下今天市场"等会误调 Wind/股票分析）+ 🔀 与其他 agent 边界表

### 2026-06-17 鉴权升级为 cxdata 官方 SMS+协议确认机制（commit 37c58a4）

- **fetch_data.py** 改为 subprocess 调用官方 `query.py`（内置 token 管理、gzip 解码、积分计数、50 次硬限制），不再自行实现 HTTP 鉴权
- 新增 `auth.py / common.py / cxda_cache_cli.py / query.py`（拷自新版 cxdata-stock-market-information skill）
- **AGENT.md** 加 Step 1.5 鉴权前置（terms-check + status + SMS 引导）+ Step 2/2.5 session start/summary
- **analyze_data.py** 修复行业名匹配 bug：L2 标准名映射（处理 "白酒Ⅲ" → "白酒Ⅱ" 等后缀变体）+ 锚点 `industry` 字段填充
- 删除 `index-market-date` skill 目录（新版已合并到 cxdata-stock-market-information）
- 数据源 skill 目录统一改名为 `cxdata-` 前缀，SKILL.md/references 同步新版（scripts 空壳，避免恢复通用 `api_query.py`）
- 删除老版 `.env` / `auth.sh` / `.env.example`（鉴权改为 `~/.cxda-cache/` 共享缓存）

### 2026-06-12 移除 4 个通用 api_query.py（commit 0692fed）

- **问题**：通过 OpenClaw 执行 agent 时，LLM 看到 4 个 skill 目录下的通用 `api_query.py`，自主调用额外接口拉数据
- **方案**：`fetch_data.py` 内嵌 token + HTTP 请求 + 接口白名单（10 个主线分析必需接口），删除 4 个 skill 目录下的通用 `api_query.py`

### 2026-06-11 约束 LLM 不得篡改数值（commit 5484e66）

- **问题**：两次生成的报告数值不一致，LLM 自行修改综合评分、主线排序、锚点个股等关键数值
- **方案**：rules.md 加约束，所有数值由 Python 脚本固定，LLM 只负责文字解读

### 2026-05-26 情绪周期评分 v2.2 修复

- 广度维度（40%）：涨停数/跌停数/上涨占比分别打分再加权（不再要求三条件同时满足）
- 强度维度（35%）：综合封板数量+炸板率（不再纯看炸板率）

## 免责声明

本 Agent 仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
