"""
数据采集器自检脚本
验证所有数据源是否可用，采集示例数据
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from collectors.data_source_factory import DataSourceFactory


def check_source(collector, name: str):
    """检查单个数据源"""
    print(f"\n🔍 检查 [{name}] ...", end=" ")
    try:
        ok = collector.health_check()
        print("✅ 可用" if ok else "⚠️  不可用")
        return ok
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def demo_kline(collector, name: str, code: str):
    """演示采集K线"""
    print(f"\n📈 [{name}] 采集K线 {code} ...")
    try:
        df = collector.fetch_history_kline(code, freq="daily")
        if not df.empty:
            print(f"   ✅ {len(df)} 条数据")
            print(f"   📅 {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
            print(f"   💰 收盘价范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
            return True
        else:
            print("   ⚠️  无数据")
            return False
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False


def demo_realtime(collector, name: str, codes: list):
    """演示采集实时行情"""
    print(f"\n📡 [{name}] 实时行情 {codes} ...")
    try:
        df = collector.fetch_realtime_quotes(codes)
        if not df.empty:
            print(f"   ✅ {len(df)} 条数据")
            for _, row in df.iterrows():
                print(f"   • {row.get('code', '?')} {row.get('name', '?')}: {row.get('price', '?')}")
            return True
        else:
            print("   ⚠️  无数据")
            return False
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False


def main():
    print("=" * 60)
    print("📊  数据采集器自检脚本")
    print("=" * 60)

    factory = DataSourceFactory()
    sources = factory.list_supported_sources()
    print(f"\n📦 已注册数据源: {', '.join(sources)}")

    # 1. 健康检查
    print("\n" + "=" * 40)
    print("1️⃣  健康检查")
    status = factory.check_all_sources()
    for name, ok in status.items():
        icon = "✅" if ok else "❌"
        print(f"   {icon} {name}")

    # 2. 采集示例数据
    print("\n" + "=" * 40)
    print("2️⃣  示例数据采集")

    # 东方财富 — A股
    em = factory.get_collector("eastmoney")
    demo_kline(em, "eastmoney", "000001")
    demo_realtime(em, "eastmoney", ["000001", "600519", "300750"])

    # Baostock — A股（K线数据质量高）
    bs = factory.get_collector("baostock")
    demo_kline(bs, "baostock", "000001")

    # Yahoo — 港股
    yh = factory.get_collector("yahoo")
    demo_kline(yh, "yahoo", "0700.HK")

    # 3. 工厂自动选择测试
    print("\n" + "=" * 40)
    print("3️⃣  工厂自动选择（故障转移）")
    try:
        df = factory.get_history_kline("000001", freq="daily")
        if not df.empty:
            print(f"   ✅ 自动选择成功: {len(df)} 条, 来源: {df['source'].iloc[0]}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n" + "=" * 60)
    print("🏁  自检完成")


if __name__ == "__main__":
    main()
