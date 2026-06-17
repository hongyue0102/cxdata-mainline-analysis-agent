# A股市场主线识别 Agent

面向 A 股市场的结构分析智能分身，用户只需说"今日主线"即可获得完整的六段式市场分析报告。

## 功能

- 自动拉取三大指数行情、行业涨跌、个股行情、舆情等数据（通过财新数据平台）
- 基于涨停集中度 + 行业涨幅 + 周月趋势的四维综合评分识别主线
- 判断情绪周期（冰点/调整/修复/主升/高潮）
- 识别核心锚点个股（情绪标的/趋势中军/补涨标的）
- Agent LLM 亲自生成六段式交易报告

## 使用方式

对 Agent 说：

- "今日主线"
- "分析一下今天的市场主线"
- "主线识别 2026-05-25"

Agent 会自动：拉取数据 → 结构化分析 → AI 生成报告

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
