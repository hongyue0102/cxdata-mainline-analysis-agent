# 股票简称变动-通用 (getStkShortNameChanByCond-G)

**API_ID:** getStkShortNameChanByCond-G

#### 输入参数

| 参数名 | 参数中文名 | 数据类型 | 是否必填 | 默认值 |
|--------|------------|----------|----------|----------|
| stkCode | 股票代码 | 字符类型 | 否 |  |
| stkShortName | 股票简称 | 字符类型 | 否 |  |
| promDate | 信息公布日期 | 日期类型 | 否 |  |
| chanDate | 变动日期 | 日期类型 | 否 |  |
| chanReasPar | 变动原因 | 数值类型 | 否 |  |
| pageNum | 页码 | Integer | 是 | 1 |
| pageSize | 每页条数 | Integer | 是 | 20 |

#### 输出参数

| 参数名 | 参数中文名 | 数据类型 |
|--------|------------|----------|
| STK_CODE | 股票代码 | 字符类型 |
| STK_SHORT_NAME | 股票简称 | 字符类型 |
| SPE_SHORT_NAME | 股票拼音简称 | 字符类型 |
| PROM_DATE | 信息公布日期 | 日期类型 |
| CHAN_DATE | 变动日期 | 日期类型 |
| CHAN_REAS_PAR | 变动原因 | 数值类型 |
| IS_APL_PAR | 是否启用 | 数值类型 |
| IS_SPE_PAR | 是否特别处理 | 数值类型 |


