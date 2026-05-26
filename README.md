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

1. 安装 Python 依赖：`pip install python-dotenv`
2. 配置数据源密钥：
   - 前往 [财新数据平台](https://yun.ccxe.com.cn/data/Skills) 注册并申请 `CXDA_USER_KEY`（**平台目前处于推广期，可免费试用**）
   - 将密钥填入以下 4 个 skill 的 `scripts/.env` 中的 `CXDA_USER_KEY` 字段：
     - `skills/stock-market-information/scripts/.env`
     - `skills/stock-basic-information/scripts/.env`
     - `skills/public-opinion-stock-index/scripts/.env`
     - `skills/index-market-date/scripts/.env`
   - 数据源 Skill 已内置在 Agent 中，无需额外下载

## 目录结构

```
mainline-analysis-agent/
├── AGENT.md                          # Agent 整体人设与执行逻辑
├── SOUL.md                           # 身份、性格、能力边界
├── rules.md                          # 硬性规则
├── config.json                       # 元数据配置
├── skills/
│   ├── mainline-analysis/            # 主线识别分析 Skill
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── fetch_data.py         # 数据获取（调用内置 4 个数据源 skill）
│   │       ├── analyze_data.py       # 结构化分析（综合评分 + 情绪周期）
│   │       ├── generate_report.py    # 输出结构化 prompt（供 Agent LLM 使用）
│   │       ├── requirements.txt
│   │       └── data/                 # 中间数据（自动生成）
│   ├── stock-market-information/     # 内置数据源：行情、行业涨跌、情绪温度
│   ├── stock-basic-information/      # 内置数据源：个股行业分类
│   ├── public-opinion-stock-index/   # 内置数据源：舆情指数
│   └── index-market-date/            # 内置数据源：三大指数行情
└── README.md
```

## 免责声明

本 Agent 仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
