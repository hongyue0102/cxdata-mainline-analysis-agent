#!/usr/bin/env python3
"""
A股主线识别 - 数据获取脚本
从财新数据 API 拉取分析所需的全部数据，保存为 JSON 文件。

使用方式：
    python fetch_data.py [日期]
    示例: python fetch_data.py 2026-04-20

输出目录：data/

鉴权说明：
    本脚本通过 subprocess 调用同目录下的 query.py（cxdata 官方统一查询工具）。
    认证状态由 query.py 自动管理（读取 ~/.cxda-cache/.shared/cxda_auth.json）。
    若未认证，query.py 会返回错误，需先由 Agent 引导用户完成 auth.py 鉴权流程。
"""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
_QUERY_SCRIPT = SCRIPT_DIR / "query.py"

# ========== 业务接口（硬编码，只允许以下接口） ==========

_ALLOWED_APIS = frozenset([
    "getDIndDayQuoByCond-G",
    "getStkHotMarketByCond-G",
    "getInduDayQuoByCond-G",
    "getStkDayQuoByCond-G",
    "getStatTradeDateMainByCond-G",
    "getDStkValueMidByCond-G",
    "getDPubComInfo1ByCond-G",
    "getIndexLyricalList2ByCond-G",
    "getIndexLyricalList1ByCond-G",
    "getDStkBlockTradeByCond-G",
])


def _run_query(api_id: str, params: dict) -> dict:
    """单次 subprocess 调用 query.py api。返回解析后的 dict（含原始 status 字段）。"""
    cmd = [sys.executable, str(_QUERY_SCRIPT), "api", api_id]
    for k, v in params.items():
        cmd.append(f"{k}={v}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(SCRIPT_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"query.py 退出码 {result.returncode}, stderr: {result.stderr[:200]}")
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("query.py 无输出")
    return json.loads(stdout)


def _session_confirm():
    """调用 query.py session confirm，解除 50 次限制阻断。"""
    cmd = [sys.executable, str(_QUERY_SCRIPT), "session", "confirm"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(SCRIPT_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"session confirm 失败: {result.stderr[:200]}")


def call_api(api_id: str, params: dict) -> dict:
    """通过 query.py 调用业务接口（仅允许 _ALLOWED_APIS 中的接口）。

    query.py 内部处理：认证、token 缓存、gzip+base64 解码、积分计数、50 次限制。
    触发 50 次限制时自动调 session confirm 解除阻断并重试一次（批量取数场景）。
    返回的 dict 与原 HTTP 直连版本兼容：含 code/result/totalCount 等字段。
    """
    if api_id not in _ALLOWED_APIS:
        print(f"  [ERROR] 不允许的接口: {api_id}")
        return {"code": "error", "result": [], "totalCount": 0}

    try:
        data = _run_query(api_id, params)

        # 50 次限制触发：自动 confirm 后重试一次
        if data.get("status") == "confirmation_required":
            print(f"  [AUTO-CONFIRM] {api_id}: 触发 50 次限制，自动 confirm 后重试")
            _session_confirm()
            data = _run_query(api_id, params)

        # 认证失败不重试
        if data.get("status") in ("failed", "terms_not_accepted"):
            msg = data.get("error", "未知错误")
            print(f"  [ERROR] {api_id}: {msg}")
            return {"code": "error", "result": [], "totalCount": 0,
                    "status": data.get("status")}

        return data
    except json.JSONDecodeError as e:
        print(f"  [ERROR] {api_id}: 响应解析失败 {e}")
        return {"code": "error", "result": [], "totalCount": 0}
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] {api_id}: 调用超时（120s）")
        return {"code": "error", "result": [], "totalCount": 0}
    except Exception as e:
        print(f"  [ERROR] {api_id}: {e}")
        return {"code": "error", "result": [], "totalCount": 0}


def fetch_all_pages(api_id: str, params: dict, show_progress: bool = False) -> list:
    """自动分页拉取全部数据（每页10000条）。"""
    all_results = []
    page = 1
    total = None
    while True:
        params_copy = {**params, "pageNum": str(page), "pageSize": "10000"}
        data = call_api(api_id, params_copy)
        results = data.get("result", [])
        if not results:
            break
        all_results.extend(results)
        if page == 1:
            tc = data.get("totalCount")
            if tc is not None:
                total = int(tc)
                total_pages = -(total // -10000) if total > 0 else 1
                print(f"    totalCount={total}, 分{total_pages}页拉取")
        if show_progress and total and page % 2 == 0:
            print(f"    ... 已拉取 {len(all_results)}/{total}")
        if total is not None and len(all_results) >= total:
            break
        page += 1
        time.sleep(0.1)
    return all_results


# ========== 辅助函数 ==========

def safe_float(val, default=0.0):
    if val in (None, "", "NaN"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    return int(safe_float(val, default))


def _get_board(code):
    if not code:
        return "main"
    prefix = code[:2]
    if prefix in ("83", "87", "88", "92"):
        return "bse"
    elif prefix == "30":
        return "gem"
    elif prefix == "68":
        return "star"
    else:
        return "main"


def _get_limit_threshold(code, name):
    board = _get_board(code)
    is_st = "ST" in (name or "")
    if board == "bse":
        return 30
    elif board in ("gem", "star"):
        return 20
    else:
        return 5 if is_st else 10


def is_limit_up(r):
    pct = safe_float(r.get("PRICE_LIMIT", 0))
    threshold = _get_limit_threshold(r.get("STK_CODE", ""), r.get("STK_SHORT_NAME", ""))
    return pct >= threshold * 0.99


def is_limit_down(r):
    pct = safe_float(r.get("PRICE_LIMIT", 0))
    threshold = _get_limit_threshold(r.get("STK_CODE", ""), r.get("STK_SHORT_NAME", ""))
    return pct <= -threshold * 0.99


# ========== 主流程 ==========

def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        today = datetime.now()
        if today.weekday() == 5:
            today -= timedelta(days=1)
        elif today.weekday() == 6:
            today -= timedelta(days=2)
        date = today.strftime("%Y-%m-%d")

    t_start = time.time()

    print(f"=== A股主线识别数据获取 ===")
    print(f"目标日期: {date}")

    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    def save(filename: str, data):
        with open(output_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {filename} ({len(data)} 条)")

    # ========================================
    # 0/8 三大指数日线行情
    # ========================================
    print("[0/8] 三大指数行情...")
    INDEX_NAMES = ["上证指数", "深证成指", "创业板指"]
    index_quotes = []
    for idx_name in INDEX_NAMES:
        data = call_api("getDIndDayQuoByCond-G",
                        {"indShortName": idx_name, "tradeDate": date, "pageNum": "1", "pageSize": "1"})
        results = data.get("result", [])
        if results:
            index_quotes.append(results[0])
    save("index_quotes.json", index_quotes)

    # ========================================
    # 1/8 市场情绪温度
    # ========================================
    print("\n[1/8] 市场情绪温度...")
    heat = fetch_all_pages("getStkHotMarketByCond-G", {"endDate": date})
    save("market_heat.json", heat)

    # ========================================
    # 2/8 申万一级行业涨跌幅（按行业级别批量拉取）
    # ========================================
    print("[2/8] 申万一级行业涨跌幅（induLevel=1 批量拉取）...")

    def fetch_industry_by_level(level: str) -> list:
        all_results = []
        page = 1
        while True:
            data = call_api("getInduDayQuoByCond-G",
                            {"induLevel": level, "pageNum": str(page), "pageSize": "200"})
            results = data.get("result", [])
            if not results:
                break
            all_results.extend(results)
            tc = data.get("totalCount")
            if tc and len(all_results) >= int(tc):
                break
            page += 1
            time.sleep(0.1)
        return [r for r in all_results
                if r.get("REST_TYPE_PAR") == "后复权"
                and r.get("WEIGH_TYPE_PAR") == "流通市值加权"]

    industry_quotes = fetch_industry_by_level("1")
    if not industry_quotes:
        print("  [ERROR] 一级行业数据为空，API 调用可能失败，后续分析结果不可靠")
    industry_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_quotes.json", industry_quotes)
    print(f"  [OK] industry_quotes.json ({len(industry_quotes)} 条)")

    # ========================================
    # 2b/8 申万二级行业涨跌幅（按行业级别批量拉取）
    # ========================================
    print("[2b/8] 申万二级行业涨跌幅（induLevel=2 批量拉取）...")

    industry_l2_quotes = fetch_industry_by_level("2")
    if not industry_l2_quotes:
        print("  [ERROR] 二级行业数据为空，API 调用可能失败，后续分析结果不可靠")
    industry_l2_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_l2_quotes.json", industry_l2_quotes)
    print(f"  [OK] industry_l2_quotes.json ({len(industry_l2_quotes)} 条)")

    # ========================================
    # 3/8 全市场个股日线行情（分页拉取全部）
    # ========================================
    print("[3/8] 全市场个股日线行情...")
    all_quotes = fetch_all_pages("getStkDayQuoByCond-G", {"tradeDate": date}, show_progress=True)
    if not all_quotes:
        print("  [ERROR] 个股行情数据为空，API 调用可能失败，后续分析结果不可靠")
    valid_quotes = [r for r in all_quotes if r.get("PRICE_LIMIT") not in (None, "", "NaN")]
    valid_quotes.sort(key=lambda x: float(x.get("PRICE_LIMIT", 0)), reverse=True)

    save("stock_top_rise.json", valid_quotes[:100])
    save("stock_top_drop.json", valid_quotes[-50:] if len(valid_quotes) > 100 else [])

    all_limit_up = [r for r in valid_quotes if is_limit_up(r)]
    all_limit_down = [r for r in valid_quotes if is_limit_down(r)]
    print(f"  总成交: {len(valid_quotes)}家")
    print(f"  涨停: {len(all_limit_up)}家")
    print(f"  跌停: {len(all_limit_down)}家")

    # ========================================
    # 4/8 异动披露
    # ========================================
    print("[4/8] 异动披露...")
    abnormal = fetch_all_pages("getStatTradeDateMainByCond-G", {"endDate": date})
    save("abnormal_trade.json", abnormal)

    # ========================================
    # 5/8 涨停股市值（并发查询）
    # ========================================
    print("[5/8] 涨停股市值...")

    def query_stock_value(r):
        val = call_api("getDStkValueMidByCond-G",
                       {"stkCode": r["STK_CODE"], "endDate": date, "pageNum": "1", "pageSize": "1"})
        return val.get("result", [])

    stock_value = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(query_stock_value, r) for r in all_limit_up]
        for f in as_completed(futures):
            stock_value.extend(f.result())
    save("stock_value.json", stock_value)

    # ========================================
    # 6/8 涨停股行业分类 + 舆情（并发查询）
    # ========================================
    print("[6/8] 涨停股行业分类 + 舆情...")

    def query_stock_detail(r):
        code = r.get("STK_CODE", "")
        name = r.get("STK_SHORT_NAME", "")
        ind_data = call_api("getDPubComInfo1ByCond-G",
                            {"stkCode": code, "pageNum": "1", "pageSize": "1"})
        ind_res = ind_data.get("result", [{}])
        info = ind_res[0] if ind_res else {}
        pos_data = call_api("getIndexLyricalList2ByCond-G",
                            {"code": code, "indexDate": date, "pageNum": "1", "pageSize": "5"})
        neg_data = call_api("getIndexLyricalList1ByCond-G",
                            {"code": code, "indexDate": date, "pageNum": "1", "pageSize": "5"})

        pos_results = pos_data.get("result", [])
        neg_results = neg_data.get("result", [])
        pos_count = sum(safe_int(p.get("ALL_REPORT_COUNT")) for p in pos_results)
        neg_count = sum(safe_int(p.get("ALL_REPORT_COUNT")) for p in neg_results)
        pos_index = max((safe_float(p.get("TODAY_INDEX")) for p in pos_results), default=0)
        neg_index = max((safe_float(p.get("TODAY_INDEX")) for p in neg_results), default=0)

        return {
            "code": code,
            "name": name,
            "sw_industry_s": info.get("INDU_CLASS_NAME_S", ""),
            "sw_industry_q": info.get("INDU_CLASS_NAME_Q", ""),
            "sw_industry_z": info.get("INDU_CLASS_NAME_Z", ""),
            "pos_count": pos_count,
            "neg_count": neg_count,
            "pos_index": pos_index,
            "neg_index": neg_index,
            "pos_titles": [p.get("REGULA_TITLE", "") or p.get("TITLE", "") for p in pos_results if p.get("REGULA_TITLE") or p.get("TITLE")],
            "neg_titles": [p.get("REGULA_TITLE", "") or p.get("TITLE", "") for p in neg_results if p.get("REGULA_TITLE") or p.get("TITLE")],
        }

    stock_detail = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(query_stock_detail, r) for r in all_limit_up]
        for f in as_completed(futures):
            stock_detail.append(f.result())
    no_industry = sum(1 for d in stock_detail if not d.get("sw_industry_s") and not d.get("sw_industry_q"))
    if no_industry > 0 and len(all_limit_up) > 0:
        print(f"  [WARN] {no_industry}/{len(all_limit_up)} 只涨停股行业分类为空，行业分类 skill 可能配置异常")
    save("stock_detail.json", stock_detail)

    # ========================================
    # 7/8 大宗交易
    # ========================================
    print("[7/8] 大宗交易...")
    block = fetch_all_pages("getDStkBlockTradeByCond-G", {"tradeDate": date})
    save("block_trade.json", block)

    # 元数据
    meta = {
        "date": date,
        "total_stocks": len(valid_quotes),
        "limit_up_count": len(all_limit_up),
        "limit_down_count": len(all_limit_down),
    }
    save("meta.json", [meta])

    elapsed = time.time() - t_start
    print(f"\n=== 完成！日期: {date}, 总成交: {len(valid_quotes)}, 涨停: {len(all_limit_up)}, 跌停: {len(all_limit_down)} ===")
    print(f"总耗时: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
