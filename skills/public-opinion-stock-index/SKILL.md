---
name: public-opinion-stock-index
description: 存储上交所、深交所、北交所上市公司舆情新闻指数、上市公司新闻热度榜等。包括股票代码，舆情统计时间，敏感舆情指数，中性舆情指数等信息。
metadata:
  version: "1.0.0"
  author: "财新数据"
  website: "guizhi.io"
  tags: ["positive-sentiment", "negative-sentiment", "neutral-sentiment", "public-opinion"]
---

# 执行标准程序 (Recommended Workflow)

当用户发起查询时，AI 推荐按照以下步骤执行：

1. **Step 1: 调用统一工具**
- 使用 `python ./scripts/api_query.py <API_ID> key=value [key=value] ...` 命令获取接口数据
- 工具会自动完成：加载配置 → 获取token → 发送请求 → 解压数据 → 输出JSON结果
- **调用方式**：所有接口统一使用 key=value 格式传参

2. **Step 2: 解析结果**
- 工具输出为格式化的JSON数据，直接解析并呈现给用户

# 数据处理说明

## 配置说明
本技能所有接口需要认证token，配置方式：
1. 在 `./scripts/.env` 文件中配置 `USER_KEY` 和 `BASE_URL`
2. 调用 `./scripts/api_query.py` 时会自动获取并使用token

## 脚本功能
`./scripts/api_query.py` 脚本功能：
- 自动加载 `./scripts/.env` 配置文件
- 自动获取 `authtoken`
- 构建请求URL并发送GET请求
- 自动处理 Base64 解码和 Gzip 解压
- 输出格式化的JSON结果

# 使用场景

- 用户查询上市公司每日敏感舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度
- 用户查询上市公司每日正面舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度



## 调用方式

所有接口统一使用 `api_query.py` 工具调用，参数采用 `key=value` 格式：

```bash
python ./scripts/api_query.py <API_ID> key=value [key=value] ...
```

## 接口清单
> ⚠️ **注意事项**：
> 1. 所有接口输入输出需要严格按照接口文档规范
> 2. 所有接口标识必须严格按照 API_ID 进行请求，不得杜撰不存在的接口
> 3. 调用接口之前必须阅读接口文档

| 接口名称 | 接口文档 | API_ID | 接口描述 |
|----------|----------|--------|----------|
| 敏感舆情指数表-通用 | ./references/getIndexLyricalList1ByCond-G.md | getIndexLyricalList1ByCond-G | 存储上市公司每日敏感舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度。 |
| 正面舆情指数表-通用 | ./references/getIndexLyricalList2ByCond-G.md | getIndexLyricalList2ByCond-G | 存储上市公司每日正面舆情指数信息。包含指数日期、股票代码、股票名称、新闻标题、今日指数、昨日指数、周平均指数、周波动、周市场平均、周市场波动、负面信息总数、主要负面信息总数、格式化后的标题、股票简称、更新日期、详情地址链接、业务分类、业务小分类等维度。 |



### API_ID 参数

- `API_ID` 用于指定要调用的具体接口，根据查询类型选择
- 示例API_ID：
- `getIndexLyricalList1ByCond-G`: 敏感舆情指数表-通用
- `getIndexLyricalList2ByCond-G`: 正面舆情指数表-通用
- 更多API_ID请参考接口[接口清单](#接口清单)

## 故障排除

- **调用失败**：检查 `./scripts/.env` 文件是否存在并正确配置了 `CXDA_USER_KEY` 和 `BASE_URL`，确认网络连接正常，token未过期。
- **输出为空**：确认输入参数是否正确，检查API_ID是否匹配查询类型。
- **权限问题**：接口返回无权限或者权限到期时，提示用户前往`https://yun.ccxe.com.cn/`联系客服
- **scripts路径问题**：文档中描述的是skill相对路径，请求时确认路径是否正确
- **相同含义字段说明**：ORG_UNI_CODE==COM_UNI_CODE;STK_UNI_CODE==BOND_UNI_CODE；如无明确说明股票代码不需要携带SH、HK等交易所代码
- **接口输入字段不明确**：接口输入参数是ORG_UNI_CODE、STK_UNI_CODE等参数时可以先通过对应的基础接口调用尝试获取，获取不到时反馈并停止
- **其他异常**：出现其他异常时停止输出并返回异常原因
