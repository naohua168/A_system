"""直接从采集器 CSV 文件填充 Redis（使用中文列头匹配）"""
import json, redis, csv, glob, os, re
from datetime import datetime

redis_client = redis.Redis(host='redis', port=6379, db=0)
CSV_DIR = '/data/raw'
TOTAL = 0

def put(key, rows, ttl, limit=200):
    global TOTAL
    if rows:
        rows = rows[:limit]
        redis_client.setex(key, ttl, json.dumps(rows, ensure_ascii=False, default=str))
        TOTAL += len(rows)
        print(f'  {key}: {len(rows)} rows (TTL={ttl}s)')
    else:
        print(f'  {key}: 无数据')

def load_csv(pattern):
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))
    if not files:
        return []
    rows = []
    for fp in files[:5]:
        try:
            with open(fp, 'r', encoding='utf-8-sig') as f:
                rows.extend(list(csv.DictReader(f)))
        except:
            pass
    return rows

# 1. stock_basic — 中文列头
rows = load_csv('stock_basic_*.csv')
rows = [{'stock_code': r.get('code',''), 'stock_name': r.get('name','')} for r in rows if r.get('code')]
put('market:stock_basic', rows, 3600)

# 2. cls_news — 中文列头
rows = load_csv('cls_news_*.csv')
seen=set(); uniq=[]
for r in rows:
    k = r.get('标题','')+r.get('发布日期','')
    if k not in seen and k.strip():
        seen.add(k)
        uniq.append({'title': r.get('标题',''), 'content': r.get('内容',''),
                     'datetime': r.get('发布日期',''), 'source': r.get('发布时间','')})
put('market:cls_news', uniq, 86400, 100)

# 3. global_news — 中文列头
rows = load_csv('global_news_*.csv')
seen=set(); uniq=[]
for r in rows:
    k = r.get('标题','')+r.get('发布时间','')
    if k not in seen and k.strip():
        seen.add(k)
        uniq.append({'title': r.get('标题',''), 'summary': r.get('摘要',''),
                     'publish_time': r.get('发布时间',''), 'url': r.get('链接','')})
put('market:global_news', uniq, 86400, 50)

# 4. northbound — 英文列头
rows = load_csv('northbound_*.csv')
seen=set(); uniq=[]
for r in rows:
    d = r.get('time','')
    if d not in seen and d:
        seen.add(d)
        uniq.append({'trade_date': d, 'hgt_yi': r.get('hgt_yi',''), 'sgt_yi': r.get('sgt_yi','')})
put('market:northbound', uniq, 86400, 20)

# 5. fund_list — 英文列头 fund_code,scale
rows = load_csv('fund_details_*.csv')
valid = [r for r in rows if re.match(r'^[0-9]+\.?[0-9]*$', r.get('scale',''))]
valid.sort(key=lambda x: float(x.get('scale',0)), reverse=True)
put('market:fund_list', valid, 86400, 200)

# 6. fund_nav — 英文列头 date,nav,daily_change,code,source
rows = load_csv('fund_nav_*.csv')
rows.sort(key=lambda x: x.get('date',''), reverse=True)
rows2 = [{'fund_code': r.get('code',''), 'nav_date': r.get('date',''),
          'nav': r.get('nav',''), 'accumulated_nav': r.get('nav','')} for r in rows if r.get('code')]
put('market:fund_nav', rows2, 86400, 100)

# 7. hot_reason — 中文列头
rows = load_csv('hot_reason_*.csv')
seen=set(); uniq=[]
for r in rows:
    c = r.get('代码','')
    if c not in seen and c:
        seen.add(c)
        uniq.append({'stock_name': r.get('名称',''), 'stock_code': c,
                     'reason': r.get('题材归因',''), 'trade_date': r.get('date','')})
put('market:hot_reason', uniq, 3600, 100)

# 8. sector_ranking — 从 stock_basic 模拟
rows2 = load_csv('stock_basic_*.csv')
sr = [{'stock_code': r.get('code',''), 'stock_name': r.get('name',''),
       'mcap_yi': r.get('mcap_yi',''), 'turnover_pct': r.get('turnover_pct','')}
      for r in rows2 if r.get('code')]
put('market:sector_ranking', sr, 3600, 200)

print(f'\n✅ 完成! 共写入 {TOTAL} 条数据到 Redis')
print(f'   Redis 现有 {redis_client.dbsize()} 个 key')
