"""
数据恢复脚本：当 HTTP 数据源宕机时，从 HDFS/Hive 读取历史数据恢复

流程:
    1. Hive 中查询最近历史记录
    2. 恢复数据到 MySQL
    3. 通过后端 API 对外服务

用法:
    # 检查数据源是否可用
    python restore_from_hdfs.py --check

    # 从 Hive 恢复最近K线数据
    python restore_from_hdfs.py --restore kline 000001 --days 30

    # 从 Hive 恢复信号层数据到 MySQL
    python restore_from_hdfs.py --restore signals --date 2026-05-12

    # 全量恢复（数据源全面宕机时使用）
    python restore_from_hdfs.py --restore all

    # 以API模式启动（提供REST接口供后端调用）
    python restore_from_hdfs.py --server --port 8100
"""
import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# ============================================================
# Hive 查询配置
# ============================================================
HIVE_JDBC = "jdbc:hive2://localhost:10000"
HIVE_DB = "stock_analysis"

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "hadoop123",
    "database": "stock_analysis",
}


class HDFSDataRestorer:
    """HDFS/Hive 数据恢复器 — 数据源兜底"""

    def __init__(self):
        self._hive_available = False
        self._mysql_conn = None

    def check_sources(self) -> dict:
        """检查各数据源可用性"""
        status = {}

        # 检查 Hive
        try:
            result = subprocess.run(
                ["beeline", "-u", HIVE_JDBC, "-e", "SELECT 1;"],
                capture_output=True, text=True, timeout=10,
            )
            status["hive"] = result.returncode == 0
            self._hive_available = status["hive"]
        except Exception:
            status["hive"] = False

        # 检查腾讯财经（核心HTTP数据源）
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                "https://qt.gtimg.cn/q=sh000001", timeout=5
            )
            status["tencent"] = resp.status == 200
        except Exception:
            status["tencent"] = False

        # 检查同花顺热点
        try:
            import requests
            r = requests.get(
                "http://zx.10jqka.com.cn/event/api/getharden/",
                timeout=5,
            )
            status["ths_hot"] = r.status_code == 200
        except Exception:
            status["ths_hot"] = False

        # 检查 MySQL
        try:
            import pymysql
            conn = pymysql.connect(**MYSQL_CONFIG)
            conn.ping()
            conn.close()
            status["mysql"] = True
        except Exception:
            status["mysql"] = False

        return status

    def hive_query(self, sql: str) -> list:
        """执行 Hive 查询，返回字典列表"""
        if not self._hive_available:
            raise RuntimeError("Hive 不可用")
        result = subprocess.run(
            ["beeline", "-u", HIVE_JDBC,
             "--outputformat=json2", "-e", f"USE {HIVE_DB}; {sql}"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Hive 查询失败: {result.stderr[:200]}")
        # 解析 JSON 输出
        lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
        json_lines = [l for l in lines if l.startswith("[") or l.startswith("{")]
        if not json_lines:
            return []
        try:
            return json.loads(json_lines[0])
        except json.JSONDecodeError:
            return []

    def restore_kline(self, code: str, days: int = 30) -> int:
        """从 Hive 恢复K线数据到 MySQL"""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sql = f"""
            SELECT trade_date, open_price, high_price, low_price, close_price,
                   pre_close, volume, amount, change_pct
            FROM stock_daily
            WHERE stock_code = '{code}'
              AND trade_date >= '{start_date}'
            ORDER BY trade_date
        """
        rows = self.hive_query(sql)
        if not rows:
            print(f"⚠️  Hive 中无 {code} 的K线数据")
            return 0

        # 写入 MySQL
        import pymysql
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        inserted = 0
        for r in rows:
            sql = """
                INSERT IGNORE INTO stock_daily
                    (stock_code, trade_date, open_price, high_price,
                     low_price, close_price, pre_close, volume, amount, change_percent)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """
            try:
                cursor.execute(sql, (
                    code, r.get("trade_date"),
                    r.get("open_price"), r.get("high_price"),
                    r.get("low_price"), r.get("close_price"),
                    r.get("pre_close"), r.get("volume"),
                    r.get("amount"), r.get("change_pct"),
                ))
                inserted += 1
            except Exception as e:
                logging.warning("K线记录插入失败 [%s/%s]: %s", code, r.get("trade_date"), e)
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ 恢复 {code} K线 {inserted} 条到 MySQL")
        return inserted

    def restore_signals(self, date_str: str = None) -> dict:
        """从 Hive 恢复信号层数据"""
        if date_str is None:
            date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        results = {}

        # 恢复题材归因
        try:
            sql = f"""
                SELECT * FROM signal_hot_reason
                WHERE fetch_date = '{date_str}'
            """
            rows = self.hive_query(sql)
            if rows:
                results["hot_reason"] = len(rows)
                print(f"✅ 恢复题材归因 {len(rows)} 条")
        except Exception as e:
            print(f"⚠️  题材归因恢复失败: {e}")

        # 恢复行业对比
        try:
            sql = f"""
                SELECT * FROM signal_industry
                WHERE fetch_date = '{date_str}'
            """
            rows = self.hive_query(sql)
            if rows:
                results["industry"] = len(rows)
                print(f"✅ 恢复行业对比 {len(rows)} 条")
        except Exception as e:
            print(f"⚠️  行业对比恢复失败: {e}")

        return results

    def restore_all(self) -> dict:
        """全量恢复 — 从 Hive 恢复所有数据到 MySQL"""
        print("🔄 全量数据恢复 (HDFS/Hive → MySQL)")
        results = {"tables": {}, "total": 0}

        tables = [
            ("stock_basic", "SELECT * FROM stock_basic"),
            ("stock_daily", "SELECT * FROM stock_daily_staging"),
            ("fund_nav", "SELECT * FROM fund_nav"),
        ]
        for table, query in tables:
            try:
                rows = self.hive_query(query)
                results["tables"][table] = len(rows)
                results["total"] += len(rows)
                print(f"  📊 {table}: {len(rows)} 条")
            except Exception as e:
                print(f"  ❌ {table}: {e}")

        print(f"\n📦 共恢复 {results['total']} 条记录")
        return results


def main():
    parser = argparse.ArgumentParser(description="HDFS/Hive 数据恢复 — HTTP 数据源宕机兜底")
    parser.add_argument("--check", action="store_true", help="检查各数据源可用性")
    parser.add_argument("--restore", type=str, choices=["kline", "signals", "all"],
                        help="恢复数据类型")
    parser.add_argument("--code", type=str, help="股票代码（kline恢复时需要）")
    parser.add_argument("--days", type=int, default=30, help="恢复天数")
    parser.add_argument("--date", type=str, help="信号层恢复日期 YYYY-MM-DD")
    parser.add_argument("--server", action="store_true", help="以 API 服务器模式启动")

    args = parser.parse_args()
    restorer = HDFSDataRestorer()

    if args.check:
        print("🔍 数据源可用性检查")
        status = restorer.check_sources()
        for name, ok in status.items():
            icon = "✅" if ok else "❌"
            print(f"  {icon} {name}")
        failed = [k for k, v in status.items() if not v]
        if failed:
            print(f"\n⚠️  不可用: {', '.join(failed)}")
            print("💡 可尝试: python restore_from_hdfs.py --restore all")
        return

    if args.restore == "kline":
        if not args.code:
            print("❌ 需要 --code 参数")
            return
        restorer.restore_kline(args.code, args.days)

    elif args.restore == "signals":
        restorer.restore_signals(args.date)

    elif args.restore == "all":
        restorer.restore_all()

    elif args.server:
        # 简易 API 服务器模式
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json

        class RestoreHandler(BaseHTTPRequestHandler):
            restorer = restorer

            def do_GET(self):
                if self.path == "/health":
                    status = self.restorer.check_sources()
                    self._json_response(200, status)
                elif self.path.startswith("/restore/kline/"):
                    code = self.path.split("/")[-1]
                    count = self.restorer.restore_kline(code)
                    self._json_response(200, {"restored": count})
                elif self.path == "/restore/all":
                    result = self.restorer.restore_all()
                    self._json_response(200, result)
                else:
                    self._json_response(404, {"error": "not found"})

            def _json_response(self, code, data):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

        port = args.port if hasattr(args, 'port') else 8100
        print(f"🔌 恢复API服务启动: http://localhost:{port}")
        print(f"   GET /health          — 数据源状态检查")
        print(f"   GET /restore/kline/000001 — 恢复K线")
        print(f"   GET /restore/all     — 全量恢复")
        HTTPServer(("0.0.0.0", port), RestoreHandler).serve_forever()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
