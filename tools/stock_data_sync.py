#!/usr/bin/env python3
"""
股票数据独立同步工具
===================
作用：从 Tushare / AKShare 下载股票数据，写入 MongoDB
特点：不依赖 TradingAgents-CN 项目，只依赖 tushare/akshare/pymongo/pandas
用法：
    # 完整同步（基础信息 + K线 + 财务数据）
    python tools/stock_data_sync.py --full
    
    # 仅下载指定股票的数据（K线）
    python tools/stock_data_sync.py --symbol 600900 --kline
    
    # 指定 Tushare token
    export TUSHARE_TOKEN=your_token_here
    python tools/stock_data_sync.py --basic --kline

数据会写入 MongoDB，默认连接 localhost:27017，数据库名 stock_data
"""

import argparse
import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import Optional

# ============================================================
# 依赖检查
# ============================================================
try:
    import pymongo
    from pymongo import MongoClient, ReplaceOne, UpdateOne
except ImportError:
    print("❌ 需要安装 pymongo: pip install pymongo")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas")
    sys.exit(1)



# ============================================================
# 自动加载 .sync_env 配置（如果环境变量未设置）
# ============================================================
import os as _os
_script_dir = _os.path.dirname(_os.path.abspath(__file__))
_env_file = _os.path.join(_script_dir, '.sync_env')
if not _os.environ.get("TUSHARE_TOKEN") and _os.path.exists(_env_file):
    try:
        with open(_env_file) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#'):
                    _k, _sep, _v = _line.partition('=')
                    if _sep and _k.strip():
                        _os.environ[_k.strip()] = _v.strip()
    except Exception:
        pass

# Tushare 和 AKShare 是可选的
TUSHARE_AVAILABLE = False
AKSHARE_AVAILABLE = False

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    pass

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    pass




# ============================================================
# Tushare 频率限制处理
# ============================================================
import time as _time

class RateLimiter:
    """Tushare API 调用频率限制器（200 次/分钟 for 2000积分）"""
    
    def __init__(self, max_calls_per_min: int = 180):
        self.max_calls = max_calls_per_min
        self.calls_in_window: list = []  # 时间戳列表
        self.total_calls = 0
        self.retries = 0
    
    def _trim_window(self):
        """移除超过 60 秒的记录"""
        now = _time.time()
        self.calls_in_window = [t for t in self.calls_in_window if now - t < 60]
    
    def wait_if_needed(self):
        """检查是否达到限制，需要等待就 sleep"""
        self._trim_window()
        if len(self.calls_in_window) >= self.max_calls:
            oldest = self.calls_in_window[0]
            wait_time = 60 - (_time.time() - oldest)
            if wait_time > 0:
                mins = int(wait_time // 60)
                secs = int(wait_time % 60)
                print(f"  ⏳ 达到 API 限制，等待 {mins}分{secs}秒...")
                while wait_time > 0:
                    if wait_time >= 5:
                        _time.sleep(5)
                        wait_time -= 5
                        print(f"  ⏳ 继续等待 {int(wait_time)}秒...")
                    else:
                        _time.sleep(wait_time)
                        wait_time = 0
            self.calls_in_window = []
    
    def record_call(self):
        """记录一次 API 调用"""
        self.calls_in_window.append(_time.time())
        self.total_calls += 1
    
    def call(self, pro, api_name: str, max_retries: int = 3, **kwargs):
        """带频率限制的 Tushare API 调用"""
        last_error = None
        for attempt in range(max_retries):
            try:
                self.wait_if_needed()
                api_func = getattr(pro, api_name)
                result = api_func(**kwargs)
                self.record_call()
                return result
            except Exception as e:
                last_error = e
                err_str = str(e)
                # 频率限制
                if "次数超限" in err_str or "over " in err_str.lower() or "limit" in err_str.lower() or "frequency" in err_str.lower():
                    wait = 65
                    print(f"  ⚠️ 频率限制，等待 {wait}秒后重试...")
                    _time.sleep(wait)
                    self.calls_in_window = []
                    continue
                # 网络错误
                if "timeout" in err_str.lower() or "connection" in err_str.lower() or "reset" in err_str.lower():
                    wait = 10 * (attempt + 1)
                    print(f"  ⚠️ 网络错误，{wait}秒后重试 ({attempt+1}/{max_retries})...")
                    _time.sleep(wait)
                    continue
                # 其他错误直接抛出
                if attempt == max_retries - 1:
                    raise
                _time.sleep(5)
        raise last_error


# 全局单例
_limiter = RateLimiter()

def ts_call(pro, api_name: str, **kwargs):
    """简化的 Tushare API 调用函数"""
    return _limiter.call(pro, api_name, **kwargs)

# ============================================================
# 配置
# ============================================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "stock_data")
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "200"))


def get_mongo():
    """获取 MongoDB 连接"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return client, db


# ============================================================
# 股票基础信息
# ============================================================
def sync_basic_info_tushare(db, force: bool = False) -> int:
    """从 Tushare 同步全部 A 股基础信息"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        print("⚠️ Tushare 不可用（未安装或无 token），跳过基础信息同步")
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    collection = db["stock_basic_info"]
    count = 0

    # 获取所有 A 股列表（含已退市，status 过滤即可）
    for status in ["L", "D", "P"]:
        print(f"📡 获取状态={status} 的股票列表...")
        try:
            df = ts_call(pro, 'stock_basic', 
                exchange="", list_status=status,
                fields="ts_code,symbol,name,area,industry,market,list_date,exchange,curr_type,is_hs"
            )
            if df is None or df.empty:
                continue

            operations = []
            for _, row in df.iterrows():
                symbol = str(row.get("symbol", ""))
                if not symbol or len(symbol) < 6:
                    continue

                # 标准化 symbol（取前6位）
                symbol_6 = symbol[:6] if symbol[0].isdigit() else symbol.split(".")[0]

                doc = {
                    "symbol": symbol_6,
                    "ts_code": symbol,
                    "name": row.get("name", ""),
                    "area": row.get("area", ""),
                    "industry": row.get("industry", ""),
                    "market": row.get("market", ""),
                    "exchange": row.get("exchange", ""),
                    "list_date": str(row.get("list_date", "")),
                    "list_status": status,
                    "is_hs": row.get("is_hs", None),
                    "source": "tushare",
                    "updated_at": datetime.now(),
                }

                operations.append(ReplaceOne(
                    {"symbol": symbol_6, "source": "tushare"},
                    replacement=doc,
                    upsert=True,
                ))

            if operations:
                result = collection.bulk_write(operations, ordered=False)
                count += result.upserted_count + result.modified_count
                print(f"  ✅ 写入 {len(operations)} 条 (状态={status})")

        except Exception as e:
            print(f"  ⚠️ 获取状态={status} 失败: {e}")

    print(f"✅ 基础信息同步完成: {count} 条记录")
    return count


# ============================================================
# 日线 K 线数据
# ============================================================
def sync_kline_tushare(
    db,
    symbols: Optional[list] = None,
    start_date: str = "",
    end_date: str = "",
    period: str = "daily",
    force: bool = False,
) -> int:
    """从 Tushare 同步 K 线数据到 stock_daily_quotes"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        print("⚠️ Tushare 不可用，跳过 K 线同步")
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_daily_quotes"]

    # 默认日期
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

    # 如果没有指定股票，从 stock_basic_info 获取全部
    if not symbols:
        symbol_docs = db["stock_basic_info"].find(
            {"source": "tushare"},
            {"symbol": 1, "ts_code": 1, "_id": 0},
        )
        symbols = list(set(doc.get("symbol") or str(doc.get("ts_code", ""))[:6]
                          for doc in symbol_docs if doc.get("symbol") or doc.get("ts_code")))

    if not symbols:
        print("⚠️ 没有股票列表，请先同步基础信息")
        return 0

    # 决定 K 线接口
    period_api_map = {
        "daily": pro.daily,
        "weekly": pro.weekly,
        "monthly": pro.monthly,
    }
    api_func = period_api_map.get(period, pro.daily)
    period_label = {"daily": "日线", "weekly": "周线", "monthly": "月线"}.get(period, period)
    end_date_short = end_date[:10].replace("-", "")

    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 50 == 0:
            print(f"📊 [{idx}/{len(symbols)}] 正在同步 {period_label}...")

        try:
            # 构建 ts_code（'600900.SH' 格式）
            code_6 = str(sym).strip().zfill(6)
            if code_6.startswith("6"):
                ts_code = f"{code_6}.SH"
            elif code_6.startswith(("0", "3")):
                ts_code = f"{code_6}.SZ"
            elif code_6.startswith(("4", "8")):
                ts_code = f"{code_6}.BJ"
            else:
                ts_code = code_6

            df = api_func(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                continue

            operations = []
            for _, row in df.iterrows():
                trade_date = str(row.get("trade_date", "")).replace("-", "")
                if not trade_date or len(trade_date) != 8:
                    continue

                doc = {
                    "symbol": code_6,
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "pre_close": float(row.get("pre_close", 0)) if "pre_close" in row else None,
                    "change": float(row.get("change", 0)) if "change" in row else None,
                    "pct_chg": float(row.get("pct_chg", 0)) if "pct_chg" in row else None,
                    "vol": float(row.get("vol", 0)) if "vol" in row else None,
                    "volume": (float(row.get("vol", 0)) * 100) if "vol" in row else None,
                    "amount": (float(row.get("amount", 0)) * 1000) if "amount" in row else None,
                    "period": period,
                    "data_source": "tushare",
                    "updated_at": datetime.now(),
                }

                operations.append(ReplaceOne(
                    {"symbol": code_6, "trade_date": trade_date, "period": period, "data_source": "tushare"},
                    replacement=doc,
                    upsert=True,
                ))

            if operations:
                # 分批写入
                for i in range(0, len(operations), BATCH_SIZE):
                    batch = operations[i:i + BATCH_SIZE]
                    result = collection.bulk_write(batch, ordered=False)
                    total += result.upserted_count + result.modified_count

        except Exception as e:
            if idx % 20 == 0:
                print(f"  ⚠️ {sym} 同步失败: {e}")
            continue

    print(f"✅ {period_label}同步完成: {total} 条记录")
    return total


# ============================================================
# 财务数据
# ============================================================
def sync_financial_data_tushare(
    db,
    symbols: Optional[list] = None,
    start_date: str = "",
    end_date: str = "",
) -> int:
    """从 Tushare 同步财务数据到 stock_financial_data"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        print("⚠️ Tushare 不可用，跳过财务数据同步")
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_financial_data"]

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = "20200101"

    if not symbols:
        symbol_docs = db["stock_basic_info"].find(
            {"source": "tushare"},
            {"symbol": 1, "ts_code": 1, "_id": 0},
        )
        symbols = list(set(doc.get("symbol") or str(doc.get("ts_code", ""))[:6]
                          for doc in symbol_docs if doc.get("symbol") or doc.get("ts_code")))

    if not symbols:
        print("⚠️ 没有股票列表，请先同步基础信息")
        return 0

    # 用 income（利润表）作为财务数据的来源
    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 30 == 0:
            print(f"📊 [{idx}/{len(symbols)}] 正在同步财务数据...")

        try:
            code_6 = str(sym).strip().zfill(6)
            if code_6.startswith("6"):
                ts_code = f"{code_6}.SH"
            elif code_6.startswith(("0", "3")):
                ts_code = f"{code_6}.SZ"
            else:
                ts_code = code_6

            # 获取利润表
            df = ts_call(pro, 'income', ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                continue

            operations = []
            for _, row in df.iterrows():
                end_date_str = str(row.get("end_date", "")).replace("-", "")
                if not end_date_str or len(end_date_str) != 8:
                    continue

                # 标准化财务数据
                report_type = "annual" if end_date_str.endswith("1231") else "quarterly"

                doc = {
                    "symbol": code_6,
                    "ts_code": ts_code,
                    "report_period": end_date_str,
                    "report_type": report_type,
                    "revenue": float(row.get("revenue", 0)) if row.get("revenue") else None,
                    "operate_profit": float(row.get("operate_profit", 0)) if row.get("operate_profit") else None,
                    "total_profit": float(row.get("total_profit", 0)) if row.get("total_profit") else None,
                    "net_profit": float(row.get("net_profit", 0)) if row.get("net_profit") else None,
                    "eps": float(row.get("basic_eps", 0)) if row.get("basic_eps") else None,
                    "data_source": "tushare",
                    "updated_at": datetime.now(),
                }

                operations.append(ReplaceOne(
                    {"symbol": code_6, "report_period": end_date_str, "data_source": "tushare"},
                    replacement=doc,
                    upsert=True,
                ))

            if operations:
                result = collection.bulk_write(operations, ordered=False)
                total += result.upserted_count + result.modified_count

        except Exception as e:
            if idx % 20 == 0:
                print(f"  ⚠️ {sym} 财务数据同步失败: {e}")
            continue

    print(f"✅ 财务数据同步完成: {total} 条记录")
    return total


# ============================================================
# 实时行情
# ============================================================
def sync_realtime_quotes_akshare(db, symbols: Optional[list] = None):
    """从 AKShare 获取实时行情（不需要 token）"""
    if not AKSHARE_AVAILABLE:
        print("⚠️ AKShare 不可用，跳过实时行情")
        return 0

    collection = db["market_quotes"]

    try:
        # AKShare 实时行情
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            print("⚠️ 实时行情为空")
            return 0

        operations = []
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if not code or len(code) != 6:
                continue

            doc = {
                "symbol": code,
                "name": row.get("名称", ""),
                "current_price": float(row.get("最新价", 0)) if row.get("最新价") else None,
                "pct_chg": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                "change": float(row.get("涨跌额", 0)) if row.get("涨跌额") else None,
                "volume": float(row.get("成交量", 0)) if row.get("成交量") else None,
                "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                "amplitude": float(row.get("振幅", 0)) if row.get("振幅") else None,
                "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                "pe": float(row.get("市盈率-动态", 0)) if row.get("市盈率-动态") else None,
                "pb": float(row.get("市净率", 0)) if row.get("市净率") else None,
                "total_mv": float(row.get("总市值", 0)) if row.get("总市值") else None,
                "circ_mv": float(row.get("流通市值", 0)) if row.get("流通市值") else None,
                "data_source": "akshare",
                "updated_at": datetime.now(),
            }

            operations.append(ReplaceOne(
                {"symbol": code, "data_source": "akshare"},
                replacement=doc,
                upsert=True,
            ))

        if operations:
            result = collection.bulk_write(operations, ordered=False)
            count = result.upserted_count + result.modified_count
            print(f"✅ 实时行情同步完成: {count} 条记录")
            return count

    except Exception as e:
        print(f"❌ 实时行情同步失败: {e}")

    return 0


# ============================================================
# 创建索引
# ============================================================
def ensure_indexes(db):
    """确保 MongoDB 集合有索引"""
    indexes = {
        "stock_basic_info": [
            [("symbol", 1)],
            [("name", 1)],
            [("industry", 1)],
            [("updated_at", -1)],
        ],
        "stock_daily_quotes": [
            [("symbol", 1), ("trade_date", -1), ("period", 1)],
            [("symbol", 1), ("trade_date", -1)],
            [("trade_date", -1)],
        ],
        "stock_financial_data": [
            [("symbol", 1), ("report_period", -1)],
            [("symbol", 1), ("report_type", 1)],
            [("report_period", -1)],
            [("updated_at", -1)],
        ],
        "market_quotes": [
            [("symbol", 1)],
            [("updated_at", -1)],
        ],
    }

    for collection_name, index_list in indexes.items():
        try:
            col = db[collection_name]
            for idx in index_list:
                col.create_index(idx, background=True)
            print(f"  ✅ {collection_name} 索引已就绪")
        except Exception as e:
            print(f"  ⚠️ {collection_name} 索引创建警告: {e}")


# ============================================================
# 统计信息
# ============================================================
def print_stats(db):
    """打印数据库统计信息"""
    print("\n" + "=" * 50)
    print("📊 数据库统计")
    print("=" * 50)
    print(f"数据库: {MONGO_DB}")

    for col_name in ["stock_basic_info", "stock_daily_quotes", "stock_financial_data", "market_quotes"]:
        try:
            count = db[col_name].count_documents({})
            print(f"  {col_name}: {count} 条")
        except:
            print(f"  {col_name}: (不存在)")

    # K 线统计
    try:
        symbols = db["stock_daily_quotes"].distinct("symbol")
        print(f"  已有 K 线数据的股票: {len(symbols)} 只")
        
        # 日期范围
        pipeline = [
            {"$group": {"_id": None, "min_date": {"$min": "$trade_date"}, "max_date": {"$max": "$trade_date"}}}
        ]
        result = list(db["stock_daily_quotes"].aggregate(pipeline))
        if result:
            print(f"  K 线日期范围: {result[0].get('min_date', '?')} ~ {result[0].get('max_date', '?')}")
    except:
        pass

    print("=" * 50)


# ============================================================
# 主入口
# ============================================================
def sync_moneyflow_tushare(db, symbols: Optional[list] = None, start_date: str = "", end_date: str = ""):
    """个股资金流向: 主力/散户净流入"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_moneyflow"]

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    if not symbols:
        symbols = _get_all_symbols(db)

    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 30 == 0:
            print(f"💸 [{idx}/{len(symbols)}] 资金流向...")
        try:
            code_6 = str(sym).strip().zfill(6)
            ts_code = _to_ts_code(code_6)
            df = ts_call(pro, 'moneyflow', ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                continue
            ops = []
            for _, row in df.iterrows():
                d = str(row.get("trade_date", "")).replace("-", "")
                if len(d) != 8:
                    continue
                ops.append(ReplaceOne(
                    {"symbol": code_6, "trade_date": d},
                    replacement={
                        "symbol": code_6, "ts_code": ts_code, "trade_date": d,
                        "buy_sm_vol": float(row.get("buy_sm_vol", 0) or 0),
                        "buy_sm_amount": float(row.get("buy_sm_amount", 0) or 0),
                        "buy_md_vol": float(row.get("buy_md_vol", 0) or 0),
                        "buy_md_amount": float(row.get("buy_md_amount", 0) or 0),
                        "buy_lg_vol": float(row.get("buy_lg_vol", 0) or 0),
                        "buy_lg_amount": float(row.get("buy_lg_amount", 0) or 0),
                        "buy_elg_vol": float(row.get("buy_elg_vol", 0) or 0),
                        "buy_elg_amount": float(row.get("buy_elg_amount", 0) or 0),
                        "net_mf_vol": float(row.get("net_mf_vol", 0) or 0),
                        "net_mf_amount": float(row.get("net_mf_amount", 0) or 0),
                        "data_source": "tushare", "updated_at": datetime.now(),
                    }, upsert=True))
            if ops:
                r = collection.bulk_write(ops, ordered=False)
                total += r.upserted_count + r.modified_count
        except Exception:
            continue
    print(f"✅ 资金流向同步完成: {total} 条")
    return total


# ============================================================
# 融资融券（2000积分）
# ============================================================
def sync_margin_tushare(db, symbols: Optional[list] = None, start_date: str = "", end_date: str = ""):
    """融资融券: 融资余额/融券余量"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_margin"]

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    if not symbols:
        symbols = _get_all_symbols(db)

    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 30 == 0:
            print(f"💰 [{idx}/{len(symbols)}] 融资融券...")
        try:
            code_6 = str(sym).strip().zfill(6)
            ts_code = _to_ts_code(code_6)
            df = ts_call(pro, 'margin', ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                continue
            ops = []
            for _, row in df.iterrows():
                d = str(row.get("trade_date", "")).replace("-", "")
                if len(d) != 8:
                    continue
                ops.append(ReplaceOne(
                    {"symbol": code_6, "trade_date": d},
                    replacement={
                        "symbol": code_6, "ts_code": ts_code, "trade_date": d,
                        "rzye": float(row.get("rzye", 0) or 0),
                        "rzmre": float(row.get("rzmre", 0) or 0),
                        "rqye": float(row.get("rqye", 0) or 0),
                        "rqyl": float(row.get("rqyl", 0) or 0),
                        "rzrqye": float(row.get("rzrqye", 0) or 0),
                        "data_source": "tushare", "updated_at": datetime.now(),
                    }, upsert=True))
            if ops:
                r = collection.bulk_write(ops, ordered=False)
                total += r.upserted_count + r.modified_count
        except Exception:
            continue
    print(f"✅ 融资融券同步完成: {total} 条")
    return total


# ============================================================
# 十大股东（2000积分）
# ============================================================
def sync_top10_holders_tushare(db, symbols: Optional[list] = None):
    """十大股东"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_top10_holders"]

    if not symbols:
        symbols = _get_all_symbols(db)

    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 30 == 0:
            print(f"🏛️  [{idx}/{len(symbols)}] 十大股东...")
        try:
            code_6 = str(sym).strip().zfill(6)
            ts_code = _to_ts_code(code_6)
            df = ts_call(pro, 'top10_holders', ts_code=ts_code)
            if df is None or df.empty:
                continue
            ops = []
            for _, row in df.iterrows():
                end_date_str = str(row.get("end_date", "")).replace("-", "")
                if len(end_date_str) != 8:
                    continue
                ops.append(ReplaceOne(
                    {"symbol": code_6, "end_date": end_date_str, "holder_name": str(row.get("holder_name", ""))},
                    replacement={
                        "symbol": code_6, "ts_code": ts_code,
                        "end_date": end_date_str,
                        "holder_name": str(row.get("holder_name", "")),
                        "hold_amount": float(row.get("hold_amount", 0) or 0),
                        "hold_ratio": float(row.get("hold_ratio", 0) or 0),
                        "data_source": "tushare", "updated_at": datetime.now(),
                    }, upsert=True))
            if ops:
                r = collection.bulk_write(ops, ordered=False)
                total += r.upserted_count + r.modified_count
        except Exception:
            continue
    print(f"✅ 十大股东同步完成: {total} 条")
    return total


# ============================================================
# 业绩预告（2000积分）
# ============================================================
def sync_forecast_tushare(db, symbols: Optional[list] = None, start_date: str = "", end_date: str = ""):
    """业绩预告"""
    if not TUSHARE_AVAILABLE or not TUSHARE_TOKEN:
        return 0

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    collection = db["stock_forecast"]

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = "20200101"
    if not symbols:
        symbols = _get_all_symbols(db)

    total = 0
    for idx, sym in enumerate(symbols):
        if idx % 30 == 0:
            print(f"🔮 [{idx}/{len(symbols)}] 业绩预告...")
        try:
            code_6 = str(sym).strip().zfill(6)
            ts_code = _to_ts_code(code_6)
            df = ts_call(pro, 'forecast', ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                continue
            ops = []
            for _, row in df.iterrows():
                end_date_str = str(row.get("end_date", "")).replace("-", "")
                if len(end_date_str) != 8:
                    continue
                ops.append(ReplaceOne(
                    {"symbol": code_6, "end_date": end_date_str, "data_source": "tushare"},
                    replacement={
                        "symbol": code_6, "ts_code": ts_code,
                        "end_date": end_date_str,
                        "type": str(row.get("type", "")),
                        "p_change_min": float(row.get("p_change_min", 0) or 0),
                        "p_change_max": float(row.get("p_change_max", 0) or 0),
                        "net_profit_min": float(row.get("net_profit_min", 0) or 0),
                        "net_profit_max": float(row.get("net_profit_max", 0) or 0),
                        "data_source": "tushare", "updated_at": datetime.now(),
                    }, upsert=True))
            if ops:
                r = collection.bulk_write(ops, ordered=False)
                total += r.upserted_count + r.modified_count
        except Exception:
            continue
    print(f"✅ 业绩预告同步完成: {total} 条")
    return total


# ============================================================
# 辅助函数
# ============================================================
def _to_ts_code(code_6: str) -> str:
    """6位代码转 ts_code 格式"""
    if code_6.startswith("6"):
        return f"{code_6}.SH"
    elif code_6.startswith(("0", "3")):
        return f"{code_6}.SZ"
    elif code_6.startswith(("4", "8")):
        return f"{code_6}.BJ"
    return code_6


def _get_all_symbols(db) -> list:
    """从 stock_basic_info 获取全部股票代码"""
    docs = db["stock_basic_info"].find({"source": "tushare"}, {"symbol": 1, "_id": 0})
    return list(set(d.get("symbol") for d in docs if d.get("symbol")))


# ============================================================
# 更新索引创建
# ============================================================
def _add_extra_indexes(db):
    """额外的索引"""
    extra = {
        "stock_moneyflow": [
            [("symbol", 1), ("trade_date", -1)],
        ],
        "stock_margin": [
            [("symbol", 1), ("trade_date", -1)],
        ],
        "stock_top10_holders": [
            [("symbol", 1), ("end_date", -1)],
        ],
        "stock_forecast": [
            [("symbol", 1), ("end_date", -1)],
        ],
    }
    for col_name, idx_list in extra.items():
        try:
            col = db[col_name]
            for idx in idx_list:
                col.create_index(idx, background=True)
        except Exception:
            pass


# ============================================================
# 更新 main() 函数支持新增参数
# ============================================================
# 在 main() 的 parser 里追加以下参数（粘贴到现有 argparse 区域）：
#   parser.add_argument("--moneyflow", action="store_true", help="同步资金流向")
#   parser.add_argument("--margin", action="store_true", help="同步融资融券")
#   parser.add_argument("--top10", action="store_true", help="同步十大股东")
#   parser.add_argument("--forecast", action="store_true", help="同步业绩预告")
#
# 并需在 args.full 逻辑里追加对应数据类型的同步调用（见下文）


def main():
    parser = argparse.ArgumentParser(
        description="📈 股票数据同步工具（独立版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整同步（推荐，2016年起）
  python tools/stock_data_sync.py --full

  # 每日增量（适合 cron，近10日K线 + 扩展数据）
  python tools/stock_data_sync.py --daily

  # 全量同步（A股成立以来所有数据）
  python tools/stock_data_sync.py --full --all

  # 仅同步基础信息
  python tools/stock_data_sync.py --basic

  # 同步某只股票的日线（最近1年）
  python tools/stock_data_sync.py --symbol 600900 --kline

  # 同步多只股票的5年日线
  python tools/stock_data_sync.py --symbol 600900,000001,000333 --kline --days 1825

  # 同步周线和月线
  python tools/stock_data_sync.py --symbol 600900 --weekly --monthly

  # 同步财务数据
  python tools/stock_data_sync.py --financial

  # 仅查看统计信息
  python tools/stock_data_sync.py --stats

环境变量:
  MONGO_URI           MongoDB 连接地址 (默认 mongodb://localhost:27017)
  MONGO_DB            数据库名 (默认 stock_data)
  TUSHARE_TOKEN       Tushare API Token
  BATCH_SIZE          写入批次大小 (默认 200)
""",
    )

    # 任务选项
    parser.add_argument("--full", action="store_true", help="完整同步（全部股票全部数据）")
    parser.add_argument("--daily", action="store_true", help="每日增量同步（基础信息 + 近10日K线 + 近30日扩展数据）")
    parser.add_argument("--basic", action="store_true", help="同步基础信息")
    parser.add_argument("--kline", action="store_true", help="同步日线 K 线")
    parser.add_argument("--weekly", action="store_true", help="同步周线")
    parser.add_argument("--monthly", action="store_true", help="同步月线")
    parser.add_argument("--financial", action="store_true", help="同步财务数据")
    parser.add_argument("--quotes", action="store_true", help="同步实时行情（AKShare）")
    parser.add_argument("--stats", action="store_true", help="打印统计信息")
    parser.add_argument("--moneyflow", action="store_true", help="同步资金流向（2000积分）")
    parser.add_argument("--margin", action="store_true", help="同步融资融券（2000积分）")
    parser.add_argument("--top10", action="store_true", help="同步十大股东（2000积分）")
    parser.add_argument("--forecast", action="store_true", help="同步业绩预告（2000积分）")
    parser.add_argument("--all", action="store_true", help="全量历史（从1990-01-01开始）")


    # 参数
    parser.add_argument("--symbol", type=str, default="", help="股票代码（多个用逗号分隔），不指定则同步全部")
    parser.add_argument("--days", type=int, default=365, help="历史数据天数（默认 365）")
    parser.add_argument("--start", type=str, default="", help="开始日期 YYYYMMDD")
    parser.add_argument("--end", type=str, default="", help="结束日期 YYYYMMDD")

    args = parser.parse_args()

    # 没参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # 解析股票列表
    symbols = None
    if args.symbol:
        symbols = [s.strip() for s in args.symbol.split(",") if s.strip()]

    # 日期
    start_date = args.start or ""
    end_date = args.end or ""

    # 连接 MongoDB
    print(f"📡 连接 MongoDB: {MONGO_URI}/{MONGO_DB}")
    client, db = get_mongo()

    try:
        # 确保索引
        print("\n🔧 确保索引...")
        ensure_indexes(db)
        _add_extra_indexes(db)
        ensure_indexes(db)

        # 完整同步
        if args.full:
            args.basic = True
            args.kline = True
            args.weekly = True
            args.monthly = True
            args.financial = True
            args.quotes = True
            args.moneyflow = True
            args.margin = True
            args.top10 = True
            args.forecast = True
            if args.days == 365 and not args.start:
                args.start = "20160101"
                args.days = 3650
            if args.all:
                args.start = "19900101"
                args.days = 36500

        # 每日增量：适合 cron 定时任务
        if args.daily:
            args.basic = True
            args.kline = True
            args.financial = True
            args.moneyflow = True
            args.margin = True
            args.forecast = True
            if not args.start:
                args.days = 10
            if args.days == 365:
                args.days = 10

        # 执行各任务
        if args.basic:
            print("\n📋 同步股票基础信息...")
            sync_basic_info_tushare(db)

        if args.kline:
            print(f"\n📊 同步日线 K 线 (最近 {args.days} 天)...")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y%m%d")
            sync_kline_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date, period="daily")

        if args.weekly:
            print(f"\n📊 同步周线 (最近 {args.days} 天)...")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y%m%d")
            sync_kline_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date, period="weekly")

        if args.monthly:
            print(f"\n📊 同步月线 (最近 {args.days} 天)...")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y%m%d")
            sync_kline_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date, period="monthly")

        if args.financial:
            print("\n💰 同步财务数据...")
            sync_financial_data_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date)

        if args.moneyflow:
            print("\n💸 同步资金流向...")
            sync_moneyflow_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date)

        if args.margin:
            print("\n💰 同步融资融券...")
            sync_margin_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date)

        if args.top10:
            print("\n🏛️  同步十大股东...")
            sync_top10_holders_tushare(db, symbols=symbols)

        if args.forecast:
            print("\n🔮 同步业绩预告...")
            sync_forecast_tushare(db, symbols=symbols, start_date=start_date, end_date=end_date)

        if args.quotes:
            print("\n🔄 同步实时行情...")
            sync_realtime_quotes_akshare(db, symbols=symbols)

        if args.stats or not any([args.basic, args.kline, args.weekly, args.monthly, args.financial, args.quotes, args.moneyflow, args.margin, args.top10, args.forecast]):
            print_stats(db)

    finally:
        client.close()

    print("\n✅ 同步完成")


if __name__ == "__main__":
    main()


# ============================================================
# 资金流向（2000积分）
# ============================================================
