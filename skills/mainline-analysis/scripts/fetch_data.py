#!/usr/bin/env python3
"""
A股主线识别 - 数据获取脚本
从财新数据 API 拉取分析所需的全部数据，保存为 JSON 文件。

使用方式：
    python fetch_data.py [日期]
    示例: python fetch_data.py 2026-04-20

输出目录：data/
"""

import base64
import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

import requests

# 统一配置文件路径（只需配一份密钥）
_UNIFIED_ENV = Path(__file__).resolve().parent / ".env"
_TOKEN_VALID_SECONDS = 60
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

_DATA_SOURCE_INSTALL_HINT = (
    "密钥申请地址: https://yun.ccxe.com.cn/data/Skills （平台推广期，可免费试用）"
)


def _load_env() -> Dict[str, str]:
    env = {}
    if _UNIFIED_ENV.exists():
        for line in _UNIFIED_ENV.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def _save_env(env: Dict[str, str]):
    lines = []
    if _UNIFIED_ENV.exists():
        for line in _UNIFIED_ENV.read_text(encoding='utf-8').splitlines():
            if not any(line.strip().startswith(k) for k in ['AUTH_TOKEN', '# === Token']):
                lines.append(line)
    lines.extend([
        '',
        '# === Token缓存（自动管理，请勿手动修改）===',
        f'AUTH_TOKEN={env.get("AUTH_TOKEN", "")}',
        f'AUTH_TOKEN_EXPIRE={env.get("AUTH_TOKEN_EXPIRE", "")}',
    ])
    _UNIFIED_ENV.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _load_config():
    """加载配置，优先环境变量，再 .env 文件"""
    _load_env_to_os()
    config = _load_env()
    return {
        "base_url": os.environ.get('BASE_URL', '').rstrip('/') or config.get('BASE_URL', '').rstrip('/'),
        "user_key": os.environ.get('CXDA_USER_KEY') or config.get('CXDA_USER_KEY'),
    }


def _load_env_to_os():
    """将 .env 配置加载到环境变量"""
    if _UNIFIED_ENV.exists():
        with open(_UNIFIED_ENV, encoding="utf-8") as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    k, v = line.strip().split('=', 1)
                    k, v = k.strip(), v.strip()
                    if k and not os.environ.get(k):
                        os.environ[k] = v


def _get_token(base_url: str, user_key: str) -> Optional[str]:
    """获取有效 token（优先缓存，过期自动刷新）"""
    env = _load_env()
    cached_token = env.get('AUTH_TOKEN')
    try:
        expire = datetime.strptime(env.get('AUTH_TOKEN_EXPIRE', ''), '%Y-%m-%d %H:%M:%S')
        if cached_token and expire > datetime.now():
            return cached_token
    except (ValueError, TypeError):
        pass

    resp = requests.get(
        f"{base_url}/webservice/foreign_getAuthtoken.htm",
        params={"userKey": user_key},
        headers=_HEADERS,
    )
    token = json.loads(resp.text).get("result")
    if token:
        env.update({
            'AUTH_TOKEN': token,
            'AUTH_TOKEN_EXPIRE': (datetime.now() + timedelta(seconds=_TOKEN_VALID_SECONDS)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        _save_env(env)
    return token


def _check_config():
    """检查密钥是否已配置"""
    config = _load_config()
    if not config["base_url"] or not config["user_key"]:
        print("未配置 CXDA_USER_KEY，首次使用需要设置密钥。")
        print("前往 https://yun.ccxe.com.cn/data/Skills 申请（推广期可免费试用）")
        print()
        try:
            user_key = input("请输入你的 CXDA_USER_KEY: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。请手动创建 scripts/.env 并填入密钥。")
            sys.exit(1)
        if not user_key:
            print("未输入密钥，退出。")
            sys.exit(1)
        with open(_UNIFIED_ENV, "w", encoding="utf-8") as f:
            f.write("BASE_URL=http://cxapi.ccxe.com.cn/cxda\n")
            f.write(f"CXDA_USER_KEY={user_key}\n")
        os.environ["CXDA_USER_KEY"] = user_key
        os.environ["BASE_URL"] = os.environ.get("BASE_URL", "http://cxapi.ccxe.com.cn/cxda")
        print(f"✓ 密钥已保存到 {_UNIFIED_ENV}，下次无需再配")
        print()


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


def call_api(api_id: str, params: dict) -> dict:
    """直接发 HTTP 请求调用 API（仅允许 _ALLOWED_APIS 中的接口）"""
    if api_id not in _ALLOWED_APIS:
        print(f"  [ERROR] 不允许的接口: {api_id}")
        return {"code": "error", "result": [], "totalCount": 0}

    config = _load_config()
    base_url = config["base_url"]
    user_key = config["user_key"]

    if not base_url or not user_key:
        print("  [ERROR] 未配置 BASE_URL 或 CXDA_USER_KEY")
        return {"code": "error", "result": [], "totalCount": 0}

    try:
        token = _get_token(base_url, user_key)
        if not token:
            print("  [ERROR] 获取 authToken 失败")
            return {"code": "error", "result": [], "totalCount": 0}

        request_params = {"authtoken": token}
        request_params.update(params)

        resp = requests.get(
            f"{base_url}/webservice/cxdata/{api_id}.htm",
            params=request_params,
            headers=_HEADERS,
        )
        data = json.loads(gzip.decompress(base64.b64decode(resp.text.strip())).decode('utf-8'))
        return data
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

    _check_config()

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
