#!/usr/bin/env python3
"""抓取 dapanyuntu.com 的真实云图API数据"""
import os; os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
import re, requests, json, time

sess = requests.Session(); sess.trust_env = False

# 步骤1: 获取首页HTML，找JS代码中的API URL
print("=== 步骤1: 分析页面获取API地址 ===")
r = sess.get("https://dapanyuntu.com/", timeout=15, proxies={"http":None,"https":None})
html = r.text

# 找所有的<script>内容
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
print(f"外部脚本: {len(scripts)}")

# 找包含api/的URL
api_urls = re.findall(r'(?:get|fetch|ajax|url|api|src)[:=]\s*["\']([^"\']*(?:api|json|treemap|data)[^"\']*)["\']', html)
print(f"\nAPI URL模式匹配:")
for u in api_urls:
    print(f"  {u}")

# 更宽松地搜索所有URL模式
all_urls = re.findall(r'["\']([^"\'\s]*(?:api|json|treemap|data|sector|market)[^"\'\s]*)["\']', html)
print(f"\n所有候选API URL:")
seen = set()
for u in all_urls:
    if u not in seen and len(u) > 10:
        seen.add(u)
        print(f"  {u[:80]}")

# 步骤2: 尝试数据接口
print("\n=== 步骤2: 尝试常见的云图API路径 ===")
bases = ["https://dapanyuntu.com", ""]
paths = [
    "/api/market/treemap",
    "/api/treemap",
    "/api/sector-ranking",
    "/api/industry-ranking",
    "/api/market/cloud",
    "/treemap-data",
    "/api/stock/treemap",
]
for base in bases:
    for path in paths:
        url = base + path
        try:
            r2 = sess.get(url, timeout=5, proxies={"http":None,"https":None})
            ct = r2.headers.get("Content-Type","")
            if "json" in ct or (r2.text.startswith("{") or r2.text.startswith("[")):
                print(f"  ✅ {url}: JSON数据, {len(r2.text)}字节")
                data = r2.json()
                if isinstance(data, list):
                    print(f"     数组长度: {len(data)}")
                    if len(data) > 0:
                        print(f"     第一个元素: {str(data[0])[:100]}")
                elif isinstance(data, dict):
                    print(f"     keys: {list(data.keys())[:10]}")
            elif r2.status_code == 200 and len(r2.text) > 1000:
                print(f"  📄 {url}: HTML/其他({len(r2.text)}字节)")
            else:
                print(f"  ❌ {url}: HTTP {r2.status_code}, {len(r2.text)}字节")
        except Exception as e:
            pass

print("\n=== 完成 ===")
