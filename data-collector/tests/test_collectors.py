"""
数据采集器自检脚本（基于 a-stock-data 重构）
验证所有数据源是否可用，采集示例数据
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

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
    except NotImplementedError:
        print("   ⏭️  不支持K线采集")
        return None
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
    except NotImplementedError:
        print("   ⏭️  不支持实时行情")
        return None
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False


def demo_signal_layer(factory, name: str):
    """演示信号层数据"""
    print(f"\n📶 [{name}] 信号层数据 ...")
    try:
        if name == "ths_hot":
            df = factory.get_hot_reason()
            print(f"   ✅ 当日强势股 {len(df)} 只" if not df.empty else "   ⚠️  无数据")
        elif name == "ths_northbound":
            df = factory.get_northbound_realtime()
            print(f"   ✅ 北向分钟点数 {len(df)}" if not df.empty else "   ⚠️  无数据")
        elif name == "baidu":
            result = factory.get_concept_blocks("000001")
            print(f"   ✅ 概念标签 {len(result.get('concept_tags', []))} 个")
        elif name == "akshare_ext":
            result = factory.get_industry_comparison(5)
            print(f"   ✅ 行业对比: 共 {result['total']} 个行业")
        return True
    except NotImplementedError:
        print("   ⏭️  不支持信号层")
        return None
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False


def main():
    print("=" * 60)
    print("📊  数据采集器自检脚本 (a-stock-data)")
    print("=" * 60)

    factory = DataSourceFactory()
    sources = factory.list_supported_sources()
    print(f"\n📦 已注册数据源 ({len(sources)}): {', '.join(sources)}")

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

    # mootdx — K线 + 实时行情
    mtdx = factory.get_collector("mootdx")
    demo_kline(mtdx, "mootdx", "000001")

    # 腾讯财经 — 实时行情（含PE/PB/市值）
    tc = factory.get_collector("tencent")
    demo_realtime(tc, "tencent", ["000001", "600519", "300750"])

    # 3. 信号层演示
    print("\n" + "=" * 40)
    print("3️⃣  信号层演示 (a-stock-data 新增)")
    for name in ["ths_hot", "ths_northbound", "baidu", "akshare_ext"]:
        demo_signal_layer(factory, name)

    # 4. 工厂自动选择测试（故障转移）
    print("\n" + "=" * 40)
    print("4️⃣  工厂自动选择（故障转移）")
    try:
        df = factory.get_history_kline("000001", freq="daily")
        if not df.empty:
            print(f"   ✅ 自动选择成功: {len(df)} 条, 来源: {df['source'].iloc[0]}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    try:
        df = factory.get_realtime_quotes(["000001"])
        if not df.empty:
            print(f"   ✅ 实时行情成功: {len(df)} 条, 来源: {df['source'].iloc[0]}")
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    print("\n" + "=" * 60)
    print("🏁  自检完成")


if __name__ == "__main__":
    main()
