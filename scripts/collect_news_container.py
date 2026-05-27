#!/usr/bin/env python3
"""
容器内: akshare采集新闻数据 → 输出JSON
运行: docker exec data-collector python3 /tmp/collect_news_container.py
"""
import os, sys, json
os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import akshare as ak
import pandas as pd

result = {}

# ====== 1. 财联社快讯 ======
try:
    df = ak.stock_info_global_cls()
    result["cls_news"] = df.to_dict(orient="records")
    print(f"cls_news: {len(df)} records", file=sys.stderr)
except Exception as e:
    result["cls_news"] = []
    print(f"cls_news FAILED: {e}", file=sys.stderr)

# ====== 2. 全球财经资讯 ======
try:
    df = ak.stock_info_global_em()
    result["global_news"] = df.to_dict(orient="records")
    print(f"global_news: {len(df)} records", file=sys.stderr)
except Exception as e:
    result["global_news"] = []
    print(f"global_news FAILED: {e}", file=sys.stderr)

# ====== 3. 个股新闻 (从stdin读股票代码列表) ======
codes_str = sys.argv[1] if len(sys.argv) > 1 else ""
codes = codes_str.split(",") if codes_str else []
stock_news = []

for i, code in enumerate(codes):
    code = code.strip()
    if not code: continue
    try:
        df = ak.stock_news_em(symbol=code)
        for _, row in df.iterrows():
            stock_news.append({
                "code": code,
                "title": str(row.get("新闻标题", "")),
                "content": str(row.get("新闻内容", "")),
                "time": str(row.get("发布时间", "")),
                "source": str(row.get("文章来源", "")),
                "url": str(row.get("新闻链接", "")),
            })
    except: pass
    if (i+1) % 500 == 0:
        print(f"stock_news progress: {i+1}/{len(codes)}, records={len(stock_news)}", file=sys.stderr)

result["stock_news"] = stock_news
print(f"stock_news: {len(stock_news)} records from {len(codes)} stocks", file=sys.stderr)

# 输出JSON (stdout) - 处理date类型
def convert_dates(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    return str(obj)

sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
sys.stdout.flush()
