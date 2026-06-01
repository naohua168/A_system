"""
获取全市场股票→行业映射，写入 Redis market:stock_industry

用法:
  # 写入 Redis（默认 localhost:6379）
  python scripts/fetch_industry_map.py

  # 指定 Redis 地址
  python scripts/fetch_industry_map.py --redis-host 192.168.1.100 --redis-port 6379

  # 仅输出 JSON 不写 Redis
  python scripts/fetch_industry_map.py --dry-run
"""
import argparse
import json
import sys
import time
from typing import Dict


def fetch_via_akshare() -> Dict[str, str]:
    """用 akshare 获取全市场行业映射"""
    import akshare as ak

    boards = ak.stock_board_industry_name_em()
    mapping: Dict[str, str] = {}
    total = len(boards)
    for i, (_, row) in enumerate(boards.iterrows()):
        name = row['board_name']
        try:
            cons = ak.stock_board_industry_cons_em(symbol=name)
            codes = cons['代码'].tolist()
            for code in codes:
                code = str(code).strip().zfill(6)
                # 取一级行业（银行 → 银行， 化学原料 → 化学原料）
                mapping[code] = name
        except Exception as e:
            print(f'  [{i+1}/{total}] ⚠️ {name}: {e}', file=sys.stderr)
        if (i + 1) % 10 == 0:
            print(f'  [{i+1}/{total}] {name} → {len(mapping)} stocks', file=sys.stderr)
        time.sleep(0.5)  # 限流

    print(f'  ✓ 完成: {len(mapping)} stocks, {total} industries', file=sys.stderr)
    return mapping


def write_to_redis(mapping: Dict[str, str], host: str = 'localhost', port: int = 6379):
    """写入 Redis market:stock_industry (7天TTL)"""
    import redis as redis_mod
    r = redis_mod.Redis(host=host, port=port, db=0)
    r.setex('market:stock_industry', 604800, json.dumps(mapping, ensure_ascii=False))
    print(f'  ✓ 已写入 Redis {host}:{port}  →  market:stock_industry ({len(mapping)} 条)', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='获取股票行业映射')
    parser.add_argument('--redis-host', default='localhost', help='Redis 主机')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis 端口')
    parser.add_argument('--dry-run', action='store_true', help='仅输出 JSON，不写 Redis')
    args = parser.parse_args()

    print('📦 获取全市场行业映射...', file=sys.stderr)
    mapping = fetch_via_akshare()

    if args.dry_run:
        print(json.dumps(mapping, ensure_ascii=False, indent=2))
        return

    write_to_redis(mapping, args.redis_host, args.redis_port)
    print('✅ 完成！auto_seed.py 下次运行时将自动聚合板块K线', file=sys.stderr)


if __name__ == '__main__':
    main()
