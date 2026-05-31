"""
数据层自愈管道 — CSV→Redis，全量真实数据不模拟
每 20 分钟自动运行，确保所有 Redis key 不因 TTL 过期
"""
import sys
sys.path.insert(0, '/app/pylib')
import json, redis, csv, glob, os, re, time
from datetime import datetime

CSV_DIR = '/data/raw'
REDIS_HOST = 'redis'

r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

# ── TTL 策略 ──
TTL_LONG = 604800       # 7 天（基础数据）
TTL_MEDIUM = 86400      # 24 小时（动态数据）
TTL_SHORT = 3600        # 1 小时（高频数据）

def latest_csv(pattern):
    """取最新 CSV 的行"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))
    if not files: return []
    fp = files[-1]
    try:
        with open(fp, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    except:
        return []

def to_camel(o):
    """递归转换 dict keys 为 camelCase"""
    if isinstance(o, dict):
        return {snake_to_camel(k): to_camel(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [to_camel(i) for i in o]
    return o

S2C_OVERRIDE = {'pe_ttm': 'pe', 'change_pct': 'changePct', 'change_amt': 'change', 'mcap_yi': 'mcapYi',
                'turnover_pct': 'turnoverPct', 'up_count': 'upCount', 'down_count': 'downCount',
                'hgt_yi': 'hgtYi', 'sgt_yi': 'sgtYi', 'index_code': 'indexCode',
                'index_name': 'indexName', 'stock_code': 'stockCode', 'stock_name': 'stockName',
                'trade_date': 'tradeDate', 'publish_time': 'publishTime', 'fund_code': 'fundCode',
                'industry': 'industryName', 'close': 'closePoint', 'open': 'openPoint',
                'high': 'highPoint', 'low': 'lowPoint', 'volume': 'volume'}

def snake_to_camel(name):
    if name in S2C_OVERRIDE: return S2C_OVERRIDE[name]
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

NUM_FIELDS = {'price','pe','pb','mcapYi','turnoverPct','changePct','change',
              'openPoint','closePoint','highPoint','lowPoint','volume','amount',
              'openPrice','closePrice','highPrice','lowPrice','preClose','lastClose','turnoverRate',
              'stockCount','totalAmount','stocks','upCount','downCount',
              'hgtYi','sgtYi'}

def fix_types(o):
    """递归将已知数值字段从字符串转为数字"""
    if isinstance(o, dict):
        return {k: (float(v) if k in NUM_FIELDS and isinstance(v, str) and v else fix_types(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [fix_types(i) for i in o]
    return o

def safe_write(key, data, ttl=TTL_LONG, limit=None):
    """写 Redis：已有 TTL>600 时不覆盖；自动转 camelCase + 数值类型"""
    if not data: return 0
    if limit: data = data[:limit]
    try:
        if r.exists(key) and r.ttl(key) > 600:
            return 0
    except:
        pass
    try:
        data = fix_types(to_camel(data))
        r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
        return len(data) if isinstance(data, list) else 1
    except:
        return 0

def safe_write_no_skip(key, data, ttl=TTL_LONG, limit=None):
    """写 Redis：强制写入（不检查 TTL）；自动转 camelCase + 数值类型"""
    if not data: return 0
    if limit: data = data[:limit]
    try:
        data = fix_types(to_camel(data))
        r.setex(key, ttl, json.dumps(data, ensure_ascii=False, default=str))
        return len(data) if isinstance(data, list) else 1
    except:
        return 0



def fill_static():
    """从 CSV 填充全部真实数据 — 不生成任何模拟数据"""
    total = 0

    # ════════════════════════════════════════════
    # 1. stock_basic (5,542只全量 + price/pe/pb/市值)
    # ════════════════════════════════════════════
    tq = latest_csv('tencent_quote_*.csv')
    if tq:
        sb_list = []
        for r in tq:
            code = r.get('stock_code', '')
            if not code:
                continue
            sb_list.append({
                'stock_code': code,
                'stock_name': r.get('stock_name', ''),
                'price': r.get('price', '0'),
                'pe_ttm': r.get('pe_ttm', ''),
                'pb': r.get('pb', ''),
                'mcap_yi': r.get('mcap_yi', '0'),
                'turnover_pct': r.get('turnover_pct', '0'),
                'change_pct': r.get('change_pct', '0'),
                'change_amt': r.get('change_amt', '0'),
                'last_close': r.get('last_close', '0'),
                'volume': r.get('volume', '0'),
                'amount_wan': r.get('amount_wan', '0'),
            })
        cnt = safe_write('market:stock_basic', sb_list, TTL_LONG)
        print(f'  stock_basic: {len(sb_list)} (tencent_quote)')
        total += cnt

        # 同时写入 detail_{code}（个股详情）
        detail_cnt = 0
        for r in tq:
            code = r.get('stock_code', '')
            if not code:
                continue
            detail = {
                'stock_code': code,
                'stock_name': r.get('stock_name', ''),
                'price': r.get('price', '0'),
                'pe_ttm': r.get('pe_ttm', ''),
                'pb': r.get('pb', ''),
                'mcap_yi': r.get('mcap_yi', '0'),
                'turnover_pct': r.get('turnover_pct', '0'),
                'change_pct': r.get('change_pct', '0'),
            }
            detail = to_camel(detail)
            try:
                if not (r.exists(f'market:detail_{code}') and r.ttl(f'market:detail_{code}') > 600):
                    r.setex(f'market:detail_{code}', TTL_LONG,
                            json.dumps(detail, ensure_ascii=False, default=str))
                    detail_cnt += 1
            except:
                pass
        print(f'  detail_*: {detail_cnt} stocks')
        total += detail_cnt

        # 写入 sector_ranking（同源数据）
        sr_list = [{'stock_code': r['stock_code'], 'stock_name': r.get('stock_name',''),
                     'mcap_yi': r.get('mcap_yi','0'), 'turnover_pct': r.get('turnover_pct','0')}
                   for r in tq]
        safe_write('market:sector_ranking', sr_list, TTL_MEDIUM)
        print(f'  sector_ranking: {len(sr_list)}')
        total += len(sr_list)
    else:
        print('  ** tencent_quote CSV 不存在！stock_basic & detail 写入跳过 **')

    # ════════════════════════════════════════════
    # 2. 指数 (index_list)
    # ════════════════════════════════════════════
    idx = latest_csv('tencent_index_*.csv')
    if idx:
        idx_list = []
        for r in idx:
            code = r.get('index_code', '').lstrip('sh').lstrip('sz')
            idx_list.append({
                'index_code': code or r.get('index_code',''),
                'index_name': r.get('index_name',''),
                'close_point': r.get('price', '0'),
                'change_pct': r.get('change_pct', '0'),
            })
        cnt = safe_write('market:index_list', idx_list, TTL_LONG)
        print(f'  index_list: {len(idx_list)}')
        total += cnt
    else:
        print('  ** tencent_index CSV 不存在！index_list 写入跳过 **')

    # ════════════════════════════════════════════
    # 3. 行业对比 + 行业树图 (industry_compare)
    # ════════════════════════════════════════════
    ind = latest_csv('industry_compare_*.csv')
    if ind:
        ind_comp = []
        seen = set()
        for r in ind:
            name = r.get('industry', '')
            if name in seen:
                continue
            seen.add(name)
            ind_comp.append({
                'industry': name,
                'change_pct': r.get('change_pct', '0'),
                'stock_count': int(r.get('up_count', 0) or 0) + int(r.get('down_count', 0) or 0),
                'total_amount': 0,
            })
        cnt = safe_write('market:industry_compare', ind_comp, TTL_LONG)
        print(f'  industry_compare: {len(ind_comp)}')
        total += cnt

        # 行业树图 (同源)
        treemap = [{'industry': x['industry'], 'change_pct': x['change_pct'],
                     'mcap_yi': 0, 'stocks': x['stock_count']} for x in ind_comp]
        safe_write('market:industry_treemap', treemap, TTL_LONG)
        print(f'  industry_treemap: {len(treemap)}')
        total += len(treemap)
    else:
        print('  ** industry_compare CSV 不存在！行业数据跳过 **')

    # ════════════════════════════════════════════
    # 4. 北向资金
    # ════════════════════════════════════════════
    nb = latest_csv('northbound_*.csv')
    if nb:
        seen = set()
        uniq = []
        for r in nb:
            d = r.get('time', '')
            if d not in seen and d:
                seen.add(d)
                uniq.append({'trade_date': d, 'hgt_yi': r.get('hgt_yi','0'), 'sgt_yi': r.get('sgt_yi','0')})
        safe_write('market:northbound', uniq, TTL_MEDIUM, 50)
        print(f'  northbound: {min(len(uniq),50)}')
        total += min(len(uniq), 50)
    else:
        print('  ** northbound CSV 不存在！北向资金跳过 **')

    # ════════════════════════════════════════════
    # 5. 题材热点
    # ════════════════════════════════════════════
    hr = latest_csv('hot_reason_*.csv')
    if hr:
        seen = set()
        uniq = []
        for r in hr:
            c = r.get('代码', '')
            if c not in seen and c:
                seen.add(c)
                uniq.append({'stock_code': c, 'stock_name': r.get('名称',''),
                             'reason': r.get('题材归因',''), 'trade_date': r.get('date','')})
        safe_write('market:hot_reason', uniq, TTL_MEDIUM, 200)
        print(f'  hot_reason: {min(len(uniq),200)}')
        total += min(len(uniq), 200)
    else:
        print('  ** hot_reason CSV 不存在！题材热点跳过 **')

    # ════════════════════════════════════════════
    # 6. 财联社快讯
    # ════════════════════════════════════════════
    cn = latest_csv('cls_news_*.csv')
    if cn:
        seen = set()
        uniq = []
        for r in cn:
            k = r.get('标题','') + r.get('发布日期','')
            if k not in seen and k.strip():
                seen.add(k)
                uniq.append({'title': r.get('标题',''), 'content': r.get('内容',''),
                             'datetime': r.get('发布日期',''), 'source': r.get('发布时间','')})
        safe_write('market:cls_news', uniq, TTL_MEDIUM, 200)
        print(f'  cls_news: {min(len(uniq),200)}')
        total += min(len(uniq), 200)
    else:
        print('  ** cls_news CSV 不存在！财联社快讯跳过 **')

    # ════════════════════════════════════════════
    # 7. 全球资讯
    # ════════════════════════════════════════════
    gn = latest_csv('global_news_*.csv')
    if gn:
        seen = set()
        uniq = []
        for r in gn:
            k = r.get('标题','') + r.get('发布时间','')
            if k not in seen and k.strip():
                seen.add(k)
                uniq.append({'title': r.get('标题',''), 'summary': r.get('摘要',''),
                             'publish_time': r.get('发布时间',''), 'url': r.get('链接','')})
        safe_write('market:global_news', uniq, TTL_MEDIUM, 100)
        print(f'  global_news: {min(len(uniq),100)}')
        total += min(len(uniq), 100)
    else:
        print('  ** global_news CSV 不存在！全球资讯跳过 **')

    # ════════════════════════════════════════════
    # 8. 基金列表 (26,908只，使用 fund_basic CSV)
    # ════════════════════════════════════════════
    fb = latest_csv('fund_basic_*.csv')
    if fb:
        fund_list = []
        for r in fb:
            code = r.get('fund_code', '')
            if not code:
                continue
            fund_list.append({
                'fundCode': code,
                'fundName': r.get('fund_name', ''),
                'fundType': r.get('fund_type', ''),
                'company': r.get('company', ''),
                'manager': r.get('manager', ''),
                'establishDate': r.get('establish_date', ''),
                'nav': float(r.get('nav', 0)) if r.get('nav') else 0,
                'accumulatedNav': float(r.get('accumulated_nav', 0)) if r.get('accumulated_nav') else 0,
                'scale': float(r.get('scale', 0)) if r.get('scale') else 0,
                'status': r.get('status', ''),
                # snake_case for backend compatibility
                'fund_code': code,
                'fund_name': r.get('fund_name', ''),
                'fund_type': r.get('fund_type', ''),
                'establish_date': r.get('establish_date', ''),
                'accumulated_nav': float(r.get('accumulated_nav', 0)) if r.get('accumulated_nav') else 0,
            })
        safe_write_no_skip('market:fund_list', fund_list, TTL_LONG)
        print(f'  fund_list: {len(fund_list)}')
        total += len(fund_list)
    else:
        print('  ** fund_basic CSV 不存在！基金列表跳过 **')

    # 基金净值
    fn = latest_csv('fund_nav_*.csv')
    if fn:
        fn_list = [{'fundCode': r.get('code', ''), 'navDate': r.get('date', ''),
                    'nav': float(r.get('nav', 0)) if r.get('nav') else 0,
                    'accumulatedNav': float(r.get('nav', 0)) if r.get('nav') else 0}
                   for r in fn if r.get('code')]
        safe_write('market:fund_nav', fn_list, TTL_MEDIUM, 200)
        print(f'  fund_nav: {min(len(fn_list),200)}')
        total += min(len(fn_list), 200)

    # ════════════════════════════════════════════
    # 9. 资金流向（从 fund_flow CSV 导入）
    # ════════════════════════════════════════════
    ff = latest_csv('fund_flow_*.csv')
    if ff:
        by_code = {}
        for row in ff:
            code = row.get('stock_code', '') or row.get('stockCode', '') or row.get('code', '')
            if not code:
                continue
            by_code.setdefault(code, []).append({
                'stockCode': code,
                'tradeDate': row.get('trade_date', row.get('tradeDate', '')),
                'mainIn': float(row.get('main_net', row.get('mainIn', 0)) or 0),
                'littleNetIn': float(row.get('small_net', row.get('littleNetIn', 0)) or 0),
                'mediumNetIn': float(row.get('mid_net', row.get('mediumNetIn', 0)) or 0),
                'largeNetIn': float(row.get('large_net', row.get('largeNetIn', 0)) or 0),
                'superNetIn': float(row.get('super_net', row.get('superNetIn', 0)) or 0),
            })
        ff_cnt = 0
        for code, items in by_code.items():
            safe_write(f'market:fund_flow_{code}', items, TTL_MEDIUM)
            ff_cnt += 1
        print(f'  fund_flow_*: {ff_cnt} stocks, {len(ff)} rows')
        total += ff_cnt
    else:
        print('  ** fund_flow CSV 不存在！资金流向跳过 **')

    # K线: 管道 (hive_to_redis) 负责写入真实 K 线（若运行）

    return total


def seed_all():
    """全量填充 — 只读真实 CSV，不生成模拟数据"""
    print(f'[{datetime.now():%H:%M:%S}] 数据自愈管道启动...')
    t0 = time.time()
    total = fill_static()
    elapsed = time.time() - t0
    print(f'[{datetime.now():%H:%M:%S}] 完成! {total} 条, 耗时{elapsed:.0f}s, Redis共{r.dbsize()}key')
    return total


if __name__ == '__main__':
    print('=== 数据管道 (真实数据自愈) ===')
    print(f'Redis: {REDIS_HOST}:6379, CSV: {CSV_DIR}')
    seed_all()
    while True:
        try:
            time.sleep(1200)
            seed_all()
        except Exception as e:
            print(f'[{datetime.now():%H:%M:%S}] 管道异常(20分钟后重试): {e}')
            time.sleep(1200)
