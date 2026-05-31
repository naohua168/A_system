"""强制覆盖所有 Redis 数据（不受 TTL 检查限制）"""
import sys
sys.path.insert(0, '/app/pylib')
import json, redis, csv, glob, os, re

rd = redis.Redis(host='redis', port=6379, db=0)
CSV = '/data/raw'
TTL = 604800  # 7 天

S2C = {'pe_ttm': 'pe', 'change_pct': 'changePct', 'change_amt': 'change', 'mcap_yi': 'mcapYi',
       'turnover_pct': 'turnoverPct', 'up_count': 'upCount', 'down_count': 'downCount',
       'hgt_yi': 'hgtYi', 'sgt_yi': 'sgtYi', 'industry': 'industryName',
       'trade_date': 'tradeDate', 'close': 'closePoint', 'open': 'openPoint',
       'high': 'highPoint', 'low': 'lowPoint', 'volume': 'volume'}

def latest_csv(pattern):
    files = sorted(glob.glob(os.path.join(CSV, pattern)))
    if not files: return []
    with open(files[-1], 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def to_camel(o):
    if isinstance(o, dict):
        return {S2C.get(k, k.split('_')[0] + ''.join(p.capitalize() for p in k.split('_')[1:])): to_camel(v) for k, v in o.items()}
    if isinstance(o, list):
        return [to_camel(i) for i in o]
    return o

NUM_FIELDS = {'price','pe','pb','mcapYi','turnoverPct','changePct','change',
              'openPoint','closePoint','highPoint','lowPoint','volume','amount',
              'openPrice','closePrice','highPrice','lowPrice','lastClose','turnoverRate',
              'stockCount','totalAmount','stocks','upCount','downCount',
              'hgtYi','sgtYi','amountWan','floatMcapYi','limitUp','limitDown',
              'volRatio','amplitudePct'}

def fix_types(o):
    """递归将已知数值字段从字符串转为数字"""
    if isinstance(o, dict):
        return {k: (float(v) if k in NUM_FIELDS and isinstance(v, str) and v else fix_types(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [fix_types(i) for i in o]
    return o

def force_write(key, data):
    rd.setex(key, TTL, json.dumps(fix_types(to_camel(data)), ensure_ascii=False, default=str))
    return len(data) if isinstance(data, list) else 1

# 1. stock_basic + detail + sector_ranking
tq = latest_csv('tencent_quote_*.csv')
if tq:
    sb_list = [{'stock_code': row.get('stock_code',''), 'stock_name': row.get('stock_name',''),
                 'price': row.get('price','0'), 'pe_ttm': row.get('pe_ttm',''), 'pb': row.get('pb',''),
                 'mcap_yi': row.get('mcap_yi','0'), 'turnover_pct': row.get('turnover_pct','0'),
                 'change_pct': row.get('change_pct','0'), 'change_amt': row.get('change_amt','0'),
                 'last_close': row.get('last_close','0'), 'volume': row.get('volume','0'),
                 'amount_wan': row.get('amount_wan','0')} for row in tq if row.get('stock_code')]
    force_write('market:stock_basic', sb_list)
    print(f'stock_basic: {len(sb_list)}')

    d_cnt = 0
    for row in tq:
        code = row.get('stock_code', '')
        if code:
            force_write(f'market:detail_{code}', dict(row))
            d_cnt += 1
    print(f'detail_*: {d_cnt}')

    sr = [{'stock_code': row['stock_code'], 'stock_name': row.get('stock_name',''),
            'mcap_yi': row.get('mcap_yi','0'), 'turnover_pct': row.get('turnover_pct','0')} for row in tq]
    force_write('market:sector_ranking', sr)
    print(f'sector_ranking: {len(sr)}')

# 2. index_list
idx = latest_csv('tencent_index_*.csv')
if idx:
    idx_list = [{'index_code': row.get('index_code','').lstrip('sh').lstrip('sz') or row.get('index_code',''),
                  'index_name': row.get('index_name',''), 'close_point': row.get('price','0'),
                  'change_pct': row.get('change_pct','0')} for row in idx]
    force_write('market:index_list', idx_list)
    print(f'index_list: {len(idx_list)}')

# 3. industry_compare + treemap
ind = latest_csv('industry_compare_*.csv')
if ind:
    seen = set()
    comp = []
    for row in ind:
        name = row.get('industry','')
        if name not in seen:
            seen.add(name)
            comp.append({'industry': name, 'change_pct': row.get('change_pct','0'),
                          'stock_count': int(row.get('up_count',0) or 0) + int(row.get('down_count',0) or 0),
                          'total_amount': 0})
    force_write('market:industry_compare', comp)
    treemap = [{'industry': x['industry'], 'change_pct': x['change_pct'], 'mcap_yi': 0, 'stocks': x['stock_count']} for x in comp]
    force_write('market:industry_treemap', treemap)
    print(f'industry_compare: {len(comp)}, treemap: {len(treemap)}')

# 4. northbound
nb = latest_csv('northbound_*.csv')
if nb:
    seen = set()
    uniq = []
    for row in nb:
        d = row.get('time','')
        if d not in seen:
            seen.add(d)
            uniq.append({'trade_date': d, 'hgt_yi': row.get('hgt_yi','0'), 'sgt_yi': row.get('sgt_yi','0')})
    force_write('market:northbound', uniq[:50])
    print(f'northbound: {min(len(uniq),50)}')

# 5. hot_reason
hr = latest_csv('hot_reason_*.csv')
if hr:
    seen = set()
    uniq = []
    for row in hr:
        c = row.get('代码','')
        if c not in seen:
            seen.add(c)
            uniq.append({'stock_code': c, 'stock_name': row.get('名称',''),
                          'reason': row.get('题材归因',''), 'trade_date': row.get('date','')})
    force_write('market:hot_reason', uniq[:200])
    print(f'hot_reason: {min(len(uniq),200)}')

# 6. cls_news
cn = latest_csv('cls_news_*.csv')
if cn:
    seen = set()
    uniq = []
    for row in cn:
        k = row.get('标题','') + row.get('发布日期','')
        if k not in seen:
            seen.add(k)
            uniq.append({'title': row.get('标题',''), 'content': row.get('内容',''),
                          'datetime': row.get('发布日期',''), 'source': row.get('发布时间','')})
    force_write('market:cls_news', uniq[:200])
    print(f'cls_news: {min(len(uniq),200)}')

# 7. global_news
gn = latest_csv('global_news_*.csv')
if gn:
    seen = set()
    uniq = []
    for row in gn:
        k = row.get('标题','') + row.get('发布时间','')
        if k not in seen:
            seen.add(k)
            uniq.append({'title': row.get('标题',''), 'summary': row.get('摘要',''),
                          'publish_time': row.get('发布时间',''), 'url': row.get('链接','')})
    force_write('market:global_news', uniq[:100])
    print(f'global_news: {min(len(uniq),100)}')

# 8. fund
fd = latest_csv('fund_details_*.csv')
if fd:
    valid = [row for row in fd if re.match(r'^[0-9]+\.?[0-9]*$', row.get('scale',''))]
    valid.sort(key=lambda x: float(x.get('scale',0)), reverse=True)
    force_write('market:fund_list', valid[:500])
    print(f'fund_list: {min(len(valid),500)}')

fn = latest_csv('fund_nav_*.csv')
if fn:
    fnl = [{'fund_code': row.get('code',''), 'nav_date': row.get('date',''),
             'nav': row.get('nav',''), 'accumulated_nav': row.get('nav','')}
           for row in fn if row.get('code')]
    force_write('market:fund_nav', fnl[:200])
    print(f'fund_nav: {min(len(fnl),200)}')

# 9. 财务指标（从 tencent_quote 已有字段构建）
if tq:
    fin_cnt = 0
    for row in tq:
        code = row.get('stock_code', '')
        if not code: continue
        try:
            price = float(row.get('price', 0) or 0)
            pe = float(row.get('pe_ttm', 0) or 0)
            pb = float(row.get('pb', 0) or 0)
            mcap = float(row.get('mcap_yi', 0) or 0)
            turnover = float(row.get('turnover_pct', 0) or 0)
            high = float(row.get('high', 0) or 0)
            low = float(row.get('low', 0) or 0)
            amp = round((high - low) / ((high + low) / 2) * 100, 2) if high and low else 0
            fins = [
                {"label": "市盈率 (PE)", "value": f"{pe:.2f}" if pe != 0 else "-"},
                {"label": "市净率 (PB)", "value": f"{pb:.2f}" if pb != 0 else "-"},
                {"label": "总市值", "value": f"{mcap:.2f}亿" if mcap else "-"},
                {"label": "换手率", "value": f"{turnover:.2f}%" if turnover else "-"},
                {"label": "振幅", "value": f"{amp:.2f}%" if amp else "-"},
            ]
            rd.setex(f'market:financial_{code}', TTL, json.dumps(fins, ensure_ascii=False))
            fin_cnt += 1
        except:
            pass
    print(f'financial_*: {fin_cnt} stocks')

# 10. 资金流向（从 fund_flow CSV 导入）
ff = latest_csv('fund_flow_*.csv')
if ff:
    by = {}
    for row in ff:
        code = row.get('stock_code', '') or row.get('stockCode', '') or row.get('code', '')
        if not code:
            continue
        by.setdefault(code, []).append({
            'stockCode': code,
            'tradeDate': row.get('trade_date', row.get('tradeDate', '')),
            'mainIn': float(row.get('main_net', row.get('mainIn', 0)) or 0),
            'littleNetIn': float(row.get('small_net', row.get('littleNetIn', 0)) or 0),
            'mediumNetIn': float(row.get('mid_net', row.get('mediumNetIn', 0)) or 0),
            'largeNetIn': float(row.get('large_net', row.get('largeNetIn', 0)) or 0),
            'superNetIn': float(row.get('super_net', row.get('superNetIn', 0)) or 0),
        })
    for code, items in by.items():
        rd.setex(f'market:fund_flow_{code}', TTL, json.dumps(items, ensure_ascii=False))
    print(f'fund_flow_*: {len(by)} stocks, {len(ff)} rows')
else:
    print(f'fund_flow_*: SKIP (no CSV)')

print(f'\nDBSIZE: {rd.dbsize()}')
print('Done! All data force-written with 7-day TTL')
