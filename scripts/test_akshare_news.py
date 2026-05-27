"""在Docker容器内测试akshare新闻采集"""
import os, sys
os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

import akshare as ak
import pandas as pd

print("=== 1. 财联社快讯 ===")
try:
    df = ak.stock_info_global_cls()
    print(f"  形状: {df.shape}")
    print(f"  列: {list(df.columns)[:10]}")
    print(df.head(2).to_string())
except Exception as e:
    print(f"  失败: {e}")

print("\n=== 2. 全球财经资讯 ===")
try:
    df = ak.stock_info_global_em()
    print(f"  形状: {df.shape}")
    print(f"  列: {list(df.columns)[:10]}")
    print(df.head(2).to_string())
except Exception as e:
    print(f"  失败: {e}")

print("\n=== 3. 个股新闻 ===")
for code in ["000001", "600519"]:
    try:
        df = ak.stock_news_em(symbol=code)
        print(f"  {code}: {df.shape}, 列: {list(df.columns)[:6]}")
        if len(df) > 0:
            print(f"    示例: {df.iloc[0,0]} | {df.iloc[0,1][:50] if len(df.columns)>1 else ''}")
    except Exception as e:
        print(f"  {code}: 失败 - {e}")
