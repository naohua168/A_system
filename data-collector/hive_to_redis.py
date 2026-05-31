"""
Hive→Redis 全市场管道 v3 — 字段名统一为 camelCase (前端需要)
"""
import sys, time, json, re
sys.path.insert(0, '/app/pylib')
from pyhive import hive
import redis

R = redis.Redis(host='redis', port=6379, db=0)
DD = 86400; HH = 3600; TH = 1800

def hq(sql):
    try:
        conn = hive.connect(host='hive-server', port=10000)
        c = conn.cursor(); c.execute(sql)
        cols = [d[0].split('.')[-1] for d in c.description]  # strip table prefix
        rows = [dict(zip(cols, r)) for r in c.fetchall()]
        conn.close(); return rows
    except Exception as e:
        print(f'  SQL FAIL: {e}'); return []

def snake_to_camel(name):
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

def to_camel(o):
    """递归转换所有 dict 键为 camelCase"""
    if isinstance(o, dict):
        return {snake_to_camel(k): to_camel(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [to_camel(i) for i in o]
    return o

def put(k, data, ttl):
    if data:
        R.setex(k, ttl, json.dumps(to_camel(data), ensure_ascii=False, default=str))
        return len(data)
    return 0

def safe_float(v, default=0):
    try: return float(v) if v is not None else default
    except: return default

def safe_str(v):
    return str(v or '')

# ---------- 字段名转换 ----------
def snake_to_camel(name):
    """snake_case → camelCase (通用)"""
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

# 每类数据的字段映射: {redis_key_prefix: {hive_field: frontend_field}}
# None = 使用 snake_to_camel 自动转换
FIELD_MAPS = {
    'stock': {  # market:stock_basic
        'stock_code': 'stockCode', 'stock_name': 'stockName',
        'mcap_yi': 'mcapYi', 'turnover_pct': 'turnoverPct',
        'pe_ttm': 'pe',
    },
    'detail': {
        'stock_code': 'stockCode', 'stock_name': 'stockName',
        'pe_ttm': 'pe', 'mcap_yi': 'mcapYi',
        'turnover_pct': 'turnoverPct', 'change_pct': 'changePct',
        'price': 'price',
    },
    'kline': {
        'stock_code': 'stockCode', 'stock_name': 'stockName',
        'trade_date': 'tradeDate',
        'open': 'openPrice', 'high': 'highPrice', 'low': 'lowPrice', 'close': 'closePrice',
        'change_pct': 'changePct',
    },
    'northbound': {
        'trade_date': 'tradeDate', 'hgt_yi': 'hgtYi', 'sgt_yi': 'sgtYi',
    },
    'cls_news': {
        'title': 'title', 'content': 'content', 'source': 'source',
        'datetime': 'publishTime',
    },
    'global_news': {
        'title': 'title', 'summary': 'summary', 'source': 'source',
        'publish_time': 'publishTime', 'url': 'url',
    },
    'fund_nav': {
        'fund_code': 'fundCode', 'nav_date': 'navDate',
        'nav': 'nav', 'accumulated_nav': 'accumulatedNav',
    },
    'fund': {  # market:fund_list, market:fund_nav
        'fund_code': 'fundCode', 'fund_name': 'fundName',
        'fund_type': 'fundType', 'company': 'company',
        'manager': 'manager', 'scale': 'scale', 'establish_date': 'establishDate',
        'nav': 'nav', 'accumulated_nav': 'accumulatedNav', 'nav_date': 'navDate',
    },
    'hot': {  # market:hot_reason
        'id': 'id', 'code': 'stockCode', 'name': 'stockName',
        'reason': 'reason', 'trade_date': 'tradeDate',
        'change_pct': 'changePct', 'turnover_pct': 'turnoverPct',
    },
    'sector': {  # market:sector_ranking
        'stock_code': 'stockCode', 'stock_name': 'stockName',
        'mcap_yi': 'mcapYi', 'turnover_pct': 'turnoverPct',
        'pe_ttm': 'pe',
    },
    'fund_flow': {
        'stock_code': 'stockCode', 'trade_date': 'tradeDate',
        'main_net': 'mainIn', 'small_net': 'littleNetIn',
        'mid_net': 'mediumNetIn', 'large_net': 'largeNetIn',
        'super_net': 'superNetIn',
    },
    'lockup': {
        'stock_code': 'stockCode', 'free_date': 'lockupDate',
        'lockup_type': 'lockupType', 'shares': 'shares',
        'ratio': 'floatRatio',
    },
    'industry_compare': {
        'industry': 'industryName', 'code': 'stockCode',
        'change_pct': 'changePct', 'up_count': 'upCount',
        'down_count': 'downCount',
    },
    'stock_news': {
        'stock_code': 'stockCode', 'title': 'title',
        'content': 'content', 'publish_time': 'publishTime',
        'source': 'source',
    },
    'dragon_tiger': {
        'trade_date': 'tradeDate', 'stock_code': 'stockCode',
        'stock_name': 'stockName', 'reason': 'reason',
        'net_buy_wan': 'netBuyWan', 'buy_wan': 'buyWan',
        'sell_wan': 'sellWan', 'change_pct': 'changePct',
    },
    'concept_blocks': {
        'stock_code': 'stockCode', 'block_name': 'blockName',
        'block_type': 'blockType', 'change_pct': 'changePct',
    },
    'filings': {
        'stock_code': 'stockCode', 'title': 'title',
        'type': 'filingType', 'publish_date': 'publishDate',
    },
    'index_list': {
        'index_code': 'indexCode', 'index_name': 'indexName',
        'change_pct': 'changePct', 'price': 'closePoint',
    },
    'index_kline': {
        'index_code': 'indexCode', 'trade_date': 'tradeDate',
        'open': 'openPoint', 'high': 'highPoint',
        'low': 'lowPoint', 'close': 'closePoint',
        'change_pct': 'changePct',
    },
    'max_date': {
        'trade_date': 'tradeDate',
    },
    'etf_list': {
        'fund_code': 'fundCode', 'fund_name': 'fundName',
        'fund_type': 'fundType', 'scale': 'scale',
        'nav': 'nav',
    },
}

def map_fields(rows, key_prefix):
    """按 FIELD_MAPS 转换字段名, 未列出的字段用 snake_to_camel 兜底"""
    if not rows:
        return rows
    mapping = FIELD_MAPS.get(key_prefix, {})
    result = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            camel = mapping.get(k)
            if camel is None:
                # auto-convert: skip leading 'v2' or table prefix
                clean = k.split('.')[-1] if '.' in k else k
                if clean.startswith('v2'): clean = clean[2:]
                camel = snake_to_camel(clean)
            # 数值类型转换
            if v is not None and isinstance(v, str) and camel.endswith(('Price','Point','Pct','Rate','Yi','Wan','Cap')):
                try: v = float(v)
                except: pass
            elif camel in ('changePct', 'changePercent', 'turnoverPct', 'pe', 'pb') and isinstance(v, str):
                try: v = float(v)
                except: pass
            # 布尔类型
            elif camel in ('isUpcoming',):
                v = bool(v) if not isinstance(v, bool) else v
            new_row[camel] = v
        result.append(new_row)
    return result

def sync():
    t0 = time.time()
    touched = 0

    # ========== PART 1 — 静态数据 ==========
    for key, sql, ttl, sort_fn, limit in [
        ('market:stock_basic',   'SELECT stock_code, stock_name, pe_ttm, mcap_yi, turnover_pct FROM stock_basic LIMIT 500', HH, None, 200),
        ('market:northbound',    'SELECT * FROM signal_northbound LIMIT 100', DD,
         lambda d: safe_str(d.get('trade_date','')), 20),
        ('market:cls_news',      'SELECT title, content, datetime, source FROM info_cls_news LIMIT 500', DD,
         lambda d: safe_str(d.get('datetime','')), 100),
        ('market:global_news',   'SELECT title, summary, publish_time, url FROM info_global_news LIMIT 200', DD,
         lambda d: safe_str(d.get('publish_time','')), 50),
        ('market:fund_nav',      'SELECT fund_code, nav_date, nav, accumulated_nav FROM fund_nav LIMIT 500', DD,
         lambda d: safe_str(d.get('nav_date','')), 100),
        ('market:fund_list',     "SELECT fund_code, fund_name, fund_type, company, manager, establish_date, nav, accumulated_nav, scale FROM fund_basic WHERE scale>0 LIMIT 5000", DD,
         lambda d: safe_float(d.get('scale',0)), 500),
        ('market:hot_reason',    'SELECT id, name AS stock_name, code AS stock_code, reason, trade_date, change_pct, turnover_pct FROM signal_hot_reason LIMIT 500', HH,
         None, 100),
        ('market:sector_ranking','SELECT stock_code, stock_name, mcap_yi, turnover_pct, pe_ttm FROM stock_basic LIMIT 1000', HH,
         lambda d: safe_float(d.get('mcap_yi',0)), 200),
    ]:
        data = hq(sql)
        prefix = key.split(':')[1].split('_')[0]
        # 修复字段映射键：部分 key 的 split('_')[0] 不匹配 FIELD_MAPS
        if prefix == 'cls': prefix = 'cls_news'
        elif prefix == 'global': prefix = 'global_news'
        elif prefix == 'fund': pass  # 'fund' in FIELD_MAPS
        data = map_fields(data, prefix)
        if data and sort_fn:
            data.sort(key=sort_fn, reverse=True)
            if limit: data = data[:limit]
        elif data and limit:
            data = data[:limit]
        n = put(key, data, ttl)
        if n: print(f'  {key}: {n} items')
        touched += n

    # ========== PART 2 — 每只股票一个 Key ==========
    # 2a. 个股详情
    rows = hq("SELECT stock_code, stock_name, price, pe_ttm, pb, mcap_yi, turnover_pct, change_pct FROM tencent_quote")
    if rows:
        rows = map_fields(rows, 'detail')
        for rw in rows:
            put(f'market:detail_{rw["stockCode"]}', [rw], HH)
        print(f'  market:detail_*: {len(rows)} stocks')

    # 2b. 资金流向
    flow = hq("SELECT stock_code, trade_date, main_net, small_net, mid_net, large_net, super_net FROM stock_fund_flow LIMIT 50000")
    if flow:
        flow = map_fields(flow, 'fund_flow')
        by = {}
        for rec in flow: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:fund_flow_{code}', items, HH)
        print(f'  market:fund_flow_*: {len(by)} stocks x {len(flow)} records')

    # 2c. 限售解禁
    lu = hq("SELECT stock_code, free_date, lockup_type, shares, ratio FROM stock_lockup LIMIT 50000")
    if lu:
        lu = map_fields(lu, 'lockup')
        by = {}
        for rec in lu: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:lockup_{code}', items, DD)
        upc = [{'stockCode': r['stockCode'], 'lockupDate': r['lockupDate'], 'shares': r['shares'], 'isUpcoming': True} for r in lu[:50]]
        put('market:lockup_upcoming', upc, DD)
        print(f'  market:lockup_*: {len(by)} stocks x {len(lu)} records')

    # 2d. 行业对比
    ind = hq("SELECT industry, code, change_pct, up_count, down_count FROM industry_compare")
    if ind:
        ind = map_fields(ind, 'industry_compare')
        put('market:industry_compare', ind, HH)
        print(f'  market:industry_compare: {len(ind)} records')

    # 2e. 个股新闻
    news = hq("SELECT stock_code, title, content, publish_time, source FROM stock_news LIMIT 50000")
    if news:
        news = map_fields(news, 'stock_news')
        by = {}
        for rec in news: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:news_{code}', items, DD)
        print(f'  market:news_*: {len(by)} stocks x {len(news)} records')

    # 2f. K线 (用直接字段映射避免 map_fields 开销)
    raw = hq("SELECT stock_code, trade_date, open, high, low, close, volume, amount, change_pct FROM stock_daily LIMIT 332520")
    if raw:
        by = {}
        for rec in raw:
            sc = rec['stock_code']
            by.setdefault(sc, []).append({
                'stockCode': sc, 'tradeDate': rec.get('trade_date'),
                'openPrice': safe_float(rec.get('open')), 'highPrice': safe_float(rec.get('high')),
                'lowPrice': safe_float(rec.get('low')), 'closePrice': safe_float(rec.get('close')),
                'volume': safe_float(rec.get('volume')), 'amount': safe_float(rec.get('amount')),
                'changePct': safe_float(rec.get('change_pct')),
            })
        for code, kls in by.items():
            R.setex(f'market:kline_{code}', HH, json.dumps(kls, ensure_ascii=False, default=str))
        print(f'  market:kline_*: {len(by)} stocks x {sum(len(v) for v in by.values())} records')

    # ========== PART 3 — 新增覆盖 ==========
    # 3a. 龙虎榜
    dt = hq("SELECT trade_date, stock_code, stock_name, reason, net_buy_wan, buy_wan, sell_wan, change_pct FROM dragon_tiger")
    if dt:
        dt = map_fields(dt, 'dragon_tiger')
        put('market:dragon_tiger', dt, HH)
        by = {}
        for rec in dt: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:dragon_tiger_{code}', items, HH)
        print(f'  market:dragon_tiger: {len(dt)} records')

    # 3b. 概念板块
    cb = hq("SELECT stock_code, block_name, block_type, change_pct FROM concept_blocks")
    if cb:
        cb = map_fields(cb, 'concept_blocks')
        by = {}
        for rec in cb: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:concept_blocks_{code}', items, HH)
        print(f'  market:concept_blocks_*: {len(by)} stocks')

    # 3c. 个股公告
    fl = hq("SELECT stock_code, title, type, publish_date FROM stock_filings LIMIT 50000")
    if fl:
        fl = map_fields(fl, 'filings')
        by = {}
        for rec in fl: by.setdefault(rec['stockCode'], []).append(rec)
        for code, items in by.items(): put(f'market:filings_{code}', items, DD)
        print(f'  market:filings_*: {len(by)} stocks x {len(fl)} records')

    # 3d. 大盘指数
    idx_list = hq("SELECT index_code, index_name, price, change_pct FROM tencent_index")
    if idx_list:
        idx_list = map_fields(idx_list, 'index_list')
        put('market:index_list', idx_list, TH)
        print(f'  market:index_list: {len(idx_list)} indices')
        for idx in idx_list:
            ic = idx['indexCode']
            klines = hq(f"SELECT index_code, trade_date, open, high, low, close, volume, amount, change_pct FROM index_daily WHERE index_code='{ic}' LIMIT 200")
            if klines:
                klines = map_fields(klines, 'index_kline')
                klines.sort(key=lambda x: safe_str(x.get('tradeDate','')), reverse=True)
                klines = klines[:120]
                klines.sort(key=lambda x: safe_str(x.get('tradeDate','')))
                R.setex(f'market:index_kline_{ic}', DD, json.dumps(klines, ensure_ascii=False, default=str))
                print(f'    market:index_kline_{ic}: {len(klines)} days')

    # 3e. 最新交易日 (从 stock_daily 读全部日期取最大)
    all_dates = hq("SELECT trade_date FROM stock_daily LIMIT 332520")
    if all_dates:
        dates = sorted(set(r['trade_date'] for r in all_dates), reverse=True)
        if dates:
            put('market:max_date', [{'tradeDate': dates[0]}], HH)
            print(f'  market:max_date: {dates[0]}')

    # 3f. ETF
    etf = hq("SELECT fund_code, fund_name, fund_type, nav, scale FROM fund_basic WHERE scale>0 LIMIT 500")
    if etf:
        etf = map_fields(etf, 'etf_list')
        etf_list = [e for e in etf if 'ETF' in str(e.get('fundType','')) or 'ETF' in str(e.get('fundName',''))]
        put('market:etf_list', etf_list[:100], DD)
        print(f'  market:etf_list: {len(etf_list)} ETFs')

    # 3g. 行业列表 (from industry_compare)
    inds = hq("SELECT DISTINCT industry FROM industry_compare WHERE industry IS NOT NULL AND industry != ''")
    if inds:
        put('market:industries', [r['industry'] for r in inds if r.get('industry')], DD)
        print(f'  market:industries: {len(inds)} industries')

    # ========== 完成报告 ==========
    elapsed = time.time() - t0
    total_keys = R.dbsize()
    print(f'[{time.strftime("%H:%M:%S")}] 同步完成: {touched} keys, Redis {total_keys} key ({elapsed:.0f}s)')

if __name__ == '__main__':
    print('=== Hive->Redis v3 (camelCase) ===')
    sync()
    while True:
        time.sleep(300)
        sync()
