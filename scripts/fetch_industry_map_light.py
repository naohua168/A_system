"""
轻量版：用 urllib 直接调东方财富 API 获取行业映射，写入 Redis
无需安装 akshare / requests，仅用 Python 标准库

用法:
  python scripts/fetch_industry_map_light.py
"""
import json
import sys
import time
import urllib.request
import urllib.parse
from typing import Dict

EAST_MONEY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://quote.eastmoney.com/',
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=EAST_MONEY_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def get_industry_list() -> list:
    """获取所有行业板块代码和名称"""
    url = 'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fs=m:90+t:2&fields=f12,f14'
    data = fetch_json(url)
    items = data.get('data', {}).get('diff', [])
    result = [(item['f12'], item['f14']) for item in items if item.get('f12') and item.get('f14')]
    print(f'  ✓ 行业列表: {len(result)} 个', file=sys.stderr)
    return result


def get_industry_constituents(board_code: str, board_name: str) -> dict:
    """获取行业成分股, 返回 {stockCode: industryName}"""
    url = f'http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fs=b:{board_code}&fields=f12,f14'
    data = fetch_json(url)
    items = data.get('data', {}).get('diff', [])
    mapping = {}
    for item in items:
        code = str(item.get('f12', '')).strip().zfill(6)
        if code:
            mapping[code] = board_name
    return mapping


def main():
    print('📦 获取全市场行业映射（轻量版）...', file=sys.stderr)

    industries = get_industry_list()
    if not industries:
        print('❌ 未能获取行业列表', file=sys.stderr)
        sys.exit(1)

    full_mapping: Dict[str, str] = {}
    total = len(industries)
    for i, (code, name) in enumerate(industries):
        try:
            mapping = get_industry_constituents(code, name)
            full_mapping.update(mapping)
            print(f'  [{i+1}/{total}] {name} → {len(mapping)} 只', file=sys.stderr)
        except Exception as e:
            print(f'  [{i+1}/{total}] ⚠️ {name}: {e}', file=sys.stderr)
        time.sleep(0.3)

    print(f'  ✓ 总计: {len(full_mapping)} 只股票, {total} 个行业', file=sys.stderr)

    # 写入 Redis（宿主机 127.0.0.1:6379）
    try:
        # 先 pd_sh 方式导入 redis
        try:
            import redis as rmod
            r = rmod.Redis(host='127.0.0.1', port=6379, db=0)
            r.setex('market:stock_industry', 604800, json.dumps(full_mapping, ensure_ascii=False))
            print(f'  ✅ 已写入 Redis 127.0.0.1:6379 → market:stock_industry ({len(full_mapping)} 条)', file=sys.stderr)
        except ImportError:
            print('  ⚠️ redis 模块未安装，输出 JSON 到 stdout', file=sys.stderr)
            print(json.dumps(full_mapping, ensure_ascii=False))
    except Exception as e:
        print(f'  ❌ Redis 写入失败: {e}', file=sys.stderr)
        print(json.dumps(full_mapping, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
