"""
缠论图表数据桥接 — 输出前端 ECharts 可渲染的格式

被 Spring Boot 后端以 ProcessBuilder 方式调用:
  python chanlun_bridge.py --code 600519

支持自动检测指数/股票 K 线类型，从 Redis 优先读取正确数据。
输出 JSON 格式:
  {
    "bi": [{"x0": 0, "y0": 1320, "x1": 5, "y1": 1380}],
    "zhongshu": [{"startX": 2, "endX": 8, "high": 1458.88, "low": 1452.10}],
    "fengxing": [{"type": "ding", "x": 5, "price": 1380}],
    "stats": {"top_fractals": 7, "bottom_fractals": 7, "pens": 65, "centers": 10},
    "buy_sell_points": [{"type": "buy_1", "date": "2026-01-23", "price": 1325.12}]
  }
"""
import argparse
import json
import sys
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("chanlun_bridge")

# 指数代码前缀（用于自动检测）
INDEX_PREFIXES = ('0', '399')


def _load_kline_from_redis(code: str, days: int = 365, prefer_index: bool = False) -> Optional[pd.DataFrame]:
    """从 Redis 直接读取 K 线数据，自动检测股票/指数类型"""
    import datetime as dt
    try:
        import redis as redis_mod
        rd = redis_mod.Redis(host=os.environ.get('SPRING_REDIS_HOST', 'redis'),
                             port=int(os.environ.get('SPRING_REDIS_PORT', '6379')),
                             db=0, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis 连接失败: {e}")
        return None

    # 决定读取顺序：仅当 prefer_index=True 时优先指数K线
    if prefer_index:
        keys = [f"market:index_kline_{code}", f"market:kline_{code}"]
    else:
        keys = [f"market:kline_{code}", f"market:index_kline_{code}"]

    raw = None
    for key in keys:
        try:
            raw = rd.get(key)
            if raw:
                logger.info(f"从 {key} 读取 {len(raw)} 字符")
                break
        except:
            continue

    if not raw:
        logger.warning(f"Redis 无数据: code={code}")
        return None

    # 解析数据
    try:
        records = json.loads(raw)
    except:
        return None
    if not records:
        return None

    field_map = {
        "tradeDate": "trade_date", "openPrice": "open", "closePrice": "close",
        "highPrice": "high", "lowPrice": "low", "volume": "volume", "amount": "amount",
        "openPoint": "open", "closePoint": "close", "highPoint": "high", "lowPoint": "low",
    }
    rows = []
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    for r in records:
        td_raw = str(r.get("tradeDate", ""))
        td_clean = td_raw.replace("-", "").replace("/", "")
        try:
            td_dt = dt.datetime.strptime(td_clean[:8], "%Y%m%d")
        except ValueError:
            continue
        if td_dt < cutoff:
            continue
        row = {"trade_date": td_dt.strftime("%Y-%m-%d")}
        for src_col, dst_col in field_map.items():
            val = r.get(src_col)
            if val is None:
                continue
            try:
                row[dst_col] = float(val)
            except:
                row[dst_col] = val if dst_col == "trade_date" else 0.0
        rows.append(row)

    if not rows:
        return None
    df = pd.DataFrame(rows)
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def _load_kline_from_file(kline_path: str, days: int = 365) -> pd.DataFrame:
    """从 JSON 文件加载 K 线数据（兼容保留）"""
    import datetime as dt
    try:
        with open(kline_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except:
        return pd.DataFrame()
    if not records:
        return pd.DataFrame()
    field_map = {
        "tradeDate": "trade_date", "openPrice": "open", "closePrice": "close",
        "highPrice": "high", "lowPrice": "low", "volume": "volume", "amount": "amount",
        "openPoint": "open", "closePoint": "close", "highPoint": "high", "lowPoint": "low",
    }
    rows = []
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    for r in records:
        td_raw = str(r.get("tradeDate", ""))
        td_clean = td_raw.replace("-", "").replace("/", "")
        try:
            td_dt = dt.datetime.strptime(td_clean[:8], "%Y%m%d")
        except ValueError:
            continue
        if td_dt < cutoff:
            continue
        row = {"trade_date": td_dt.strftime("%Y-%m-%d")}
        for src_col, dst_col in field_map.items():
            val = r.get(src_col)
            if val is None:
                continue
            try:
                row[dst_col] = float(val)
            except:
                row[dst_col] = val if dst_col == "trade_date" else 0.0
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def _load_kline(code: str, days: int = 365) -> pd.DataFrame:
    """从 MySQL 加载 K 线（传统方式，作为备用）"""
    from data.loader import DataLoader
    dl = DataLoader()
    df = dl.read_kline(code, days)
    dl.close()
    return df


def _run_chanlun_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """执行完整缠论分析并返回前端可渲染格式（与原逻辑相同）"""
    from chanlun.fractal import identify_fractals, merge_klines, find_fractals, filter_fractals
    from chanlun.pen import find_pens
    from chanlun.segment import find_segments
    from chanlun.central import find_centrals, identify_centrals
    from chanlun.signal import generate_signals

    work = df.copy()
    if "trade_date" in work.columns and "date" not in work.columns:
        work = work.rename(columns={"trade_date": "date"})

    merged = merge_klines(work)
    all_fractals = find_fractals(merged)
    filtered = filter_fractals(all_fractals)
    top_count = sum(1 for f in filtered if f.type == "top")
    bottom_count = sum(1 for f in filtered if f.type == "bottom")

    fengxing = []
    kline_idx_map = {}
    for i, row in work.iterrows():
        kline_idx_map[str(row.get("date", ""))] = i
    for f in filtered:
        x = kline_idx_map.get(str(f.date), 0)
        fengxing.append({
            "type": "ding" if f.type == "top" else "di",
            "x": x,
            "price": f.price,
        })

    pens_obj = find_pens(filtered)
    bi = []
    for pen in pens_obj:
        pen_x0 = kline_idx_map.get(str(pen.start_date), 0)
        pen_x1 = kline_idx_map.get(str(pen.end_date), len(work) - 1)
        bi.append({
            "x0": pen_x0,
            "y0": pen.start_price,
            "x1": pen_x1,
            "y1": pen.end_price,
        })

    segments = find_segments(pens_obj)
    centrals = find_centrals(segments)

    zhongshu = []
    for c in centrals:
        start_x = kline_idx_map.get(str(c.start_date), 0)
        end_x = kline_idx_map.get(str(c.end_date), len(work) - 1)
        zhongshu.append({
            "startX": start_x,
            "endX": end_x,
            "high": c.ZG,
            "low": c.ZD,
        })

    marked = work.copy()
    marked["fractal_type"] = ""
    marked["fractal_price"] = 0.0
    marked["fractal_strength"] = 0.0
    for f in filtered:
        idx = f.k2.idx
        if idx < len(marked):
            marked.iloc[idx, marked.columns.get_loc("fractal_type")] = f.type
            marked.iloc[idx, marked.columns.get_loc("fractal_price")] = f.price
            marked.iloc[idx, marked.columns.get_loc("fractal_strength")] = f.strength
    marked["central_ZG"] = 0.0
    marked["central_ZD"] = 0.0
    marked["central_ZF"] = 0.0
    marked["central_mid"] = 0.0
    marked["central_level"] = 0
    marked["central_extended"] = False
    for c in centrals:
        if not c.segments:
            continue
        start_idx = c.segments[0].pens[0].start_fractal.k2.idx
        end_idx = c.segments[-1].pens[-1].end_fractal.k2.idx
        if start_idx < len(marked) and end_idx < len(marked):
            for i in range(start_idx, end_idx + 1):
                marked.iloc[i, marked.columns.get_loc("central_ZG")] = c.ZG
                marked.iloc[i, marked.columns.get_loc("central_ZD")] = c.ZD
                marked.iloc[i, marked.columns.get_loc("central_ZF")] = c.ZF
                marked.iloc[i, marked.columns.get_loc("central_mid")] = c.mid_price
                marked.iloc[i, marked.columns.get_loc("central_level")] = c.level
                marked.iloc[i, marked.columns.get_loc("central_extended")] = c.extended

    signals = generate_signals(marked)
    buy_sell_points = []
    for s in signals:
        # 查找信号日期在 K 线数据中的索引（x 坐标）
        x_idx = -1
        try:
            match = marked.index[marked['date'].astype(str).str.startswith(s.date.replace('-','')[:8])]
            if len(match):
                x_idx = int(match[0])
        except Exception:
            pass
        buy_sell_points.append({
            "type": s.signal_type,
            "x": x_idx,
            "date": s.date,
            "price": s.price,
            "strength": s.strength,
            "description": s.description,
        })

    return {
        "bi": bi,
        "zhongshu": zhongshu,
        "fengxing": fengxing,
        "stats": {
            "top_fractals": top_count,
            "bottom_fractals": bottom_count,
            "pens": len(pens_obj),
            "centers": len(centrals),
            "signals": len(signals),
        },
        "buy_sell_points": buy_sell_points,
    }


def get_chanlun_data(code: str, days: int = 365, kline_file: str = None, prefer_index: bool = False) -> Dict[str, Any]:
    """获取指定股票的缠论分析数据"""
    df = None

    # 如果 Java 传入了 kline_file，检查文件数据是否与预期类型匹配
    # 若不匹配（如 000001 个股/指数混淆），自动从 Redis 读取正确数据
    if kline_file:
        try:
            with open(kline_file, "r", encoding="utf-8") as f:
                file_records = json.load(f)
            if file_records:
                first = file_records[0]
                has_stock = any(k in first for k in ("closePrice", "openPrice"))
                has_index = any(k in first for k in ("closePoint", "openPoint"))
                # 深度检测：代码以 0/399 开头但文件是股票格式（closePrice）
                # 读取关闭格判断实际价格范围：个股 < 200，指数 > 200
                if has_stock and not has_index:
                    sample_price = first.get("closePrice", first.get("openPrice", 0))
                    try:
                        sample_price = float(sample_price)
                    except:
                        sample_price = 0
                    # 价格 > 200 且代码以 0/399 开头 → 这是被错标的指数数据
                    if sample_price > 200 and code.startswith(('0', '399')):
                        df = _load_kline_from_redis(code, days, True)
                    # 价格 <= 200 且代码非 0/399 开头 → 正常个股
                    elif sample_price <= 200 and not code.startswith(('0', '399')):
                        pass  # 股票数据正常
                # 深度检测：文件是指数格式但代码非指数前缀
                if has_index and not has_stock:
                    if not code.startswith(('0', '399')):
                        df = _load_kline_from_redis(code, days, False)
        except Exception:
            pass

    # 未从文件获取到正确数据，尝试从 Redis 读取
    if df is None:
        df = _load_kline_from_redis(code, days, prefer_index)

    # Redis 失败 + 有文件 → 兜底使用文件数据
    if df is None and kline_file:
        df = _load_kline_from_file(kline_file, days)

    # MySQL 兜底
    if df is None:
        df = _load_kline(code, days)

    if df is None or df.empty or len(df) < 30:
        return {"error": f"K线数据不足 (code={code}, rows={len(df) if df is not None else 0})", "bi": [],
                "zhongshu": [], "fengxing": [], "buy_sell_points": []}

    return _run_chanlun_analysis(df)


def main():
    parser = argparse.ArgumentParser(description="缠论图表数据桥接")
    parser.add_argument("--code", required=True, help="股票代码")
    parser.add_argument("--days", type=int, default=365, help="K线天数")
    parser.add_argument("--kline-file", default=None, help="K线数据文件路径（兼容保留）")
    parser.add_argument("--type", default="auto", choices=["auto", "stock", "index"],
                        help="数据类型: auto(自动检测)/stock(个股)/index(指数)")
    args = parser.parse_args()

    # 根据 --type 决定是否优先使用指数 K 线（仅当显式指定 index 时）
    prefer_index = (args.type == "index")

    try:
        result = get_chanlun_data(args.code, args.days, args.kline_file, prefer_index)
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e), "bi": [], "zhongshu": [],
                          "fengxing": [], "buy_sell_points": []},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
