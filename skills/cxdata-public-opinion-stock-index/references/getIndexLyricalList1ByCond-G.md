# 敏感舆情指数表-通用 (getIndexLyricalList1ByCond-G)

**API_ID:** getIndexLyricalList1ByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 |
|--------|------------|----------|----------|----------|
| indexDate | 指数日期 | 日期类型(yyyy-MM-dd) | 否 |  |
| code | 股票代码 | 字符类型 | 否 |  |
| stkName | 股票名称 | 字符类型 | 否 |  |
| pageNum | 页码 | Integer | 是 | 1 |
| pageSize | 每页条数 | Integer | 是 | 20 |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| INDEX_DATE | 指数日期 | 日期类型 |
| CODE | 股票代码 | 字符类型 |
| STK_NAME | 股票名称 | 字符类型 |
| TITLE | 新闻标题 | 字符类型 |
| TODAY_INDEX | 今日指数 | 数值类型 |
| YESTERDAY_INDEX | 昨日指数 | 数值类型 |
| INDEX_AVG | 周平均指数 | 数值类型 |
| WEEK_WAVE | 周波动 | 数值类型 |
| DATEINDEX_AVG | 周市场平均 | 数值类型 |
| WEEK_ALL_WAVE | 周市场波动 | 数值类型 |
| ALL_REPORT_COUNT | 负面信息总数 | 数值类型 |
| REPORT_COUNT | 主要负面信息总数 | 数值类型 |
| REGULA_TITLE | 格式化后的标题 | 字符类型 |
| UPDATE_DATE | 更新日期 | 字符类型 |
| BUS_TYPE | 业务分类 | 数值类型 |
| BUS_SMALL_TYPE | 业务小分类 | 数值类型 |


