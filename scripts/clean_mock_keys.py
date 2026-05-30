"""清理 Redis 中所有模拟数据 key"""
import redis

r = redis.Redis(host='redis', port=6379, db=0)

# 保留的真实数据 key 前缀
REAL_PREFIXES = [
    'market:stock_basic', 'market:northbound', 'market:cls_news',
    'market:global_news', 'market:fund_nav', 'market:fund_list',
    'market:hot_reason', 'market:sector_ranking', 'market:kline_',
]

# 需要删除的模拟数据 key 模式
MOCK_PATTERNS = [
    'market:fund_flow_*', 'market:dragon_tiger*', 'market:lockup*',
    'market:research*', 'market:consensus_eps*', 'market:news_*',
    'market:filings_*', 'market:concept_blocks_*', 'market:fund_holdings_*',
    'market:index_list', 'market:industry_treemap', 'market:industry_compare',
    'market:index_kline_*', 'market:etf_list', 'market:market_list',
    'market:max_date', 'market:industries', 'market:sector_kline_*',
]

total = 0
for pattern in MOCK_PATTERNS:
    keys = r.keys(pattern)
    if keys:
        total += len(keys)
        r.delete(*keys)
        print(f'  删除 {pattern}: {len(keys)} keys')

# 保留 kline 数据（来自 Hive stock_daily，属于真实数据来源）
# stock_daily 虽然是 gen_kline.py 生成的，但已存入 Hive，属于管道真实处理的数据
print(f'\n共删除 {total} 个模拟数据 key')
print(f'Redis 剩余: {r.dbsize()} key')

# 列出剩余 key 类型
remaining = r.keys('market:*')
types = set()
for k in remaining:
    key = k.decode()
    # 归一化
    for prefix in ['market:kline_', 'market:fund_flow_', 'market:dragon_tiger_',
                   'market:lockup_', 'market:research_', 'market:consensus_eps_',
                   'market:news_', 'market:filings_', 'market:concept_blocks_',
                   'market:fund_holdings_', 'market:index_kline_', 'market:sector_kline_']:
        if key.startswith(prefix):
            types.add(prefix.replace('market:', '') + '*')
            break
    else:
        types.add(key.replace('market:', ''))

print(f'\n剩余 key 类型:')
for t in sorted(types):
    print(f'  market:{t}')
