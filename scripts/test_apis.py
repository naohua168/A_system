"""验证核心API端点是否正常工作"""
import requests, json

TOKEN = None
BASE = "http://localhost:8082/api"

def login():
    global TOKEN
    r = requests.post(f"{BASE}/user/login", 
                      json={"username":"admin","password":"admin123"}, timeout=5)
    j = r.json()
    TOKEN = j["data"]["token"]
    print(f"✅ 登录成功, token={TOKEN[:30]}...")

def test(method, path, desc, **kwargs):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if method == "GET":
        r = requests.get(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
    else:
        r = requests.post(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
    j = r.json()
    # 兼容两种返回格式: ApiResponse {code, data} 或 直接数组
    if isinstance(j, dict):
        code = j.get("code", 0)
        status = "✅" if code in (200, 201) else "❌"
        detail = ""
        if code in (200, 201) and "data" in j:
            data = j["data"]
            if isinstance(data, dict):
                records = data.get("records", data.get("list", []))
                if records:
                    detail = f" ({len(records)}条记录)"
                elif "total" in data:
                    detail = f" (total={data['total']})"
            elif isinstance(data, list):
                detail = f" ({len(data)}条)"
            elif data is not None:
                detail = f" (有数据)"
        print(f"  {status} {method} {path} — {desc}{detail}")
        if code not in (200, 201):
            print(f"     错误: {j.get('message', '未知错误')}")
    elif isinstance(j, list):
        print(f"  ✅ {method} {path} — {desc} ({len(j)}条)")
    else:
        print(f"  ✅ {method} {path} — {desc} (返回{r.status_code})")
    return j

if __name__ == "__main__":
    print("=" * 60)
    print("核心API端点验证")
    print("=" * 60)

    login()
    print()

    # 行情层
    test("GET", "/market/list?page=1&size=5", "股票列表")
    test("GET", "/market/industries", "行业列表")
    test("GET", "/market/000001", "股票详情(平安银行)")
    test("GET", "/market/kline/000001?days=5", "K线数据")
    test("GET", "/market/sector-kline?industry=银行&days=5", "板块K线")
    print()

    # 指数层
    test("GET", "/index/list", "指数列表")
    test("GET", "/index/000001/kline?days=5", "指数K线")
    print()

    # 信号层
    test("GET", "/signal/hot-reason", "题材热点")
    test("GET", "/signal/dragon-tiger/daily?date=2026-05-25", "龙虎榜daily")
    test("GET", "/signal/dragon-tiger/stock/000001", "龙虎榜个股(平安银行)")
    test("GET", "/signal/northbound/latest", "北向资金")
    test("GET", "/signal/lockup-detail/000001", "限售解禁")
    test("GET", "/signal/fund-flow/000001", "资金流向")
    test("GET", "/signal/industry-compare", "行业对比")
    test("GET", "/signal/concept-blocks/000001", "概念板块")
    print()

    # 基金层
    test("GET", "/fund/list", "基金列表")
    test("GET", "/fund/000001", "基金详情")
    test("GET", "/fund/000001/nav?days=5", "基金净值")
    test("GET", "/fund/000001/holdings", "基金持仓")
    print()

    # 资讯层
    test("GET", "/info/research/000001", "个股研报")
    test("GET", "/info/news/000001", "个股新闻")
    test("GET", "/info/consensus-eps/000001", "一致预期")
    print()

    # 分析层
    test("GET", "/analysis/sector-ranking", "行业排行")
    test("GET", "/analysis/000001/chanlun?days=60", "缠论分析")
    print()

    print("=" * 60)
    print("API端点验证完成")
    print("=" * 60)
