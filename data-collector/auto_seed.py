"""
数据层自愈管道 — CSV→Redis (纯 socket 实现, 零外部依赖)
每 20 分钟自动运行，确保所有 Redis key 不因 TTL 过期
"""
import sys, json, csv, glob, os, re, time, socket
from datetime import datetime

CSV_DIR = '/data/raw'
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# ── TTL 策略 ──
# 价格/涨跌幅数据必须短 TTL + no_skip，确保每次 auto_seed 运行都能刷新
# 静态基础数据可以长 TTL + skip，减少不必要写入
TTL_LONG = 604800       # 7 天（基础数据：行业、基金、指数列表）
TTL_MEDIUM = 86400      # 24 小时（动态数据：信号、资讯）
TTL_SHORT = 3600        # 1 小时（高频价格数据：stock_basic/detail/sector_ranking）

CSV_COL_MAP = {
    'code': 'stock_code', 'name': 'stock_name', 'date': 'trade_date',
    'time': 'trade_date', 'fetch_date': 'trade_date',
}

def latest_csv(pattern):
    """取最新 CSV 的行，统一列名"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))
    if not files:
        return []
    fp = files[-1]
    try:
        with open(fp, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # 统一列名: 新采集器用 code/name, 旧 CSV 用 stock_code/stock_name
            rows = []
            for row in reader:
                norm = {}
                for k, v in row.items():
                    nk = CSV_COL_MAP.get(k, k)
                    norm[nk] = v
                rows.append(norm)
            return rows
    except:
        return []

S2C_OVERRIDE = {'pe_ttm': 'pe', 'change_pct': 'changePct', 'change_amt': 'change', 'mcap_yi': 'mcapYi',
                'turnover_pct': 'turnoverPct', 'up_count': 'upCount', 'down_count': 'downCount',
                'hgt_yi': 'hgtYi', 'sgt_yi': 'sgtYi', 'index_code': 'indexCode',
                'index_name': 'indexName', 'stock_code': 'stockCode', 'stock_name': 'stockName',
                'trade_date': 'tradeDate', 'publish_time': 'publishTime', 'fund_code': 'fundCode',
                'industry': 'industryName', 'close': 'closePoint', 'open': 'openPoint',
                'high': 'highPoint', 'low': 'lowPoint', 'volume': 'volume'}

def snake_to_camel(name):
    if name in S2C_OVERRIDE:
        return S2C_OVERRIDE[name]
    parts = name.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

NUM_FIELDS = {'price','pe','pb','mcapYi','turnoverPct','changePct','change',
              'openPoint','closePoint','highPoint','lowPoint','volume','amount',
              'openPrice','closePrice','highPrice','lowPrice','preClose','lastClose','turnoverRate',
              'stockCount','totalAmount','stocks','upCount','downCount',
              'hgtYi','sgtYi','amountWan'}

def fix_types(o):
    if isinstance(o, dict):
        return {k: (float(v) if k in NUM_FIELDS and isinstance(v, str) and v else fix_types(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [fix_types(i) for i in o]
    return o

def to_camel(o):
    if isinstance(o, dict):
        return {snake_to_camel(k): to_camel(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [to_camel(i) for i in o]
    return o

def _redis_cmd(*args):
    """通过 socket 发送 Redis RESP 命令并返回响应"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((REDIS_HOST, REDIS_PORT))
        # Build RESP array
        resp = f'*{len(args)}\r\n'.encode()
        for a in args:
            if isinstance(a, str):
                a = a.encode('utf-8')
            resp += f'${len(a)}\r\n'.encode() + a + b'\r\n'
        s.sendall(resp)
        # Read response
        data = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\r\n' in data:
                break
        s.close()
        return data.decode('utf-8', errors='replace').strip()
    except Exception:
        return '-ERR'

def _redis_setex(key, value, ttl):
    """SETEX key ttl value via socket"""
    resp = _redis_cmd('SETEX', key, str(ttl), json.dumps(value, ensure_ascii=False, default=str))
    return resp == 'OK'

def _redis_ttl(key):
    """TTL key via socket"""
    resp = _redis_cmd('TTL', key)
    try:
        return int(resp)
    except (ValueError, TypeError):
        return -2

def _redis_get(key):
    """GET key via socket, returns parsed JSON or None"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((REDIS_HOST, REDIS_PORT))
        cmd = f'*2\r\n$3\r\nGET\r\n${len(key)}\r\n{key}\r\n'.encode()
        s.sendall(cmd)
        data = b''
        while True:
            try:
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        s.close()
        if not data:
            return None
        # Parse RESP bulk string: $<len>\r\n<data>\r\n
        if data[0:1] == b'$':
            parts = data.split(b'\r\n', 2)
            if len(parts) >= 2 and parts[0].startswith(b'$-1'):
                return None  # nil
            if len(parts) >= 3:
                return json.loads(parts[1].decode('utf-8'))
        return None
    except Exception:
        return None

def redis_setex(key, data, ttl):
    """通过 socket 写入 Redis"""
    if not data:
        return 0
    try:
        prepared = fix_types(to_camel(data))
        if _redis_setex(key, prepared, ttl):
            return len(data) if isinstance(data, list) else 1
        return 0
    except Exception:
        return 0

def safe_write(key, data, ttl=TTL_LONG, limit=None):
    """安全写入：如果 key 的 TTL > 600s 则跳过（减少不必要写入）"""
    if not data:
        return 0
    if limit:
        data = data[:limit]
    try:
        ttl_val = _redis_ttl(key)
        if ttl_val > 600:
            return 0
    except:
        pass
    return redis_setex(key, data, ttl)

def safe_write_no_skip(key, data, ttl=TTL_LONG, limit=None):
    """强制写入：不检查 TTL，覆盖现有数据"""
    if not data:
        return 0
    if limit:
        data = data[:limit]
    return redis_setex(key, data, ttl)

def safe_write_force_price(key, data, ttl=TTL_SHORT, limit=None):
    """价格数据强制写入：短 TTL + 始终覆盖，确保每次 auto_seed 都刷新"""
    if not data:
        return 0
    if limit:
        data = data[:limit]
    return redis_setex(key, data, ttl)

def fill_static():
    """
    从 CSV 填充全部真实数据 — 不生成任何模拟数据

    TTL 分层策略:
      - TTL_SHORT (1h): 价格/涨跌幅数据 (stock_basic, detail, sector_ranking)
        → safe_write_force_price: 每次 auto_seed 都强制刷新
      - TTL_MEDIUM (24h): 动态信号数据 (northbound, hot_reason, news)
        → safe_write: 检查 TTL>600 才跳过
      - TTL_LONG (7天): 静态基础数据 (index_list, industry_compare, fund_list)
        → safe_write: 首写后长时间不变
    """
    total = 0

    # ════════════════════════════════════════════
    # 1. stock_basic (全量 + price/pe/pb/市值)
    # ════════════════════════════════════════════
    # 兼容两种文件名: tencent_quote_* (旧) / realtime_* (新 run_collector)
    tq = latest_csv('realtime_*.csv') or latest_csv('tencent_quote_*.csv')
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
        # ── 价格敏感数据: 短 TTL + 强制刷新 ──
        cnt = safe_write_force_price('market:stock_basic', sb_list)
        print(f'  stock_basic: {len(sb_list)} (tencent_quote, TTL={TTL_SHORT}s)')
        total += cnt

        # detail_{code} — 每个股票一个 key，短 TTL
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
            if redis_setex(f'market:detail_{code}', detail, TTL_SHORT):
                detail_cnt += 1
        print(f'  detail_*: {detail_cnt} stocks (TTL={TTL_SHORT}s)')
        total += detail_cnt

        # sector_ranking — 全市场排行，短 TTL
        sr_list = [{'stock_code': r['stock_code'], 'stock_name': r.get('stock_name',''),
                     'mcap_yi': r.get('mcap_yi','0'), 'turnover_pct': r.get('turnover_pct','0'),
                     'change_pct': r.get('change_pct','0')}
                   for r in tq]
        safe_write_force_price('market:sector_ranking', sr_list)
        print(f'  sector_ranking: {len(sr_list)} (TTL={TTL_SHORT}s)')
        total += len(sr_list)

        # max_date
        today = ''
        for r in tq:
            td = r.get('trade_date', '') or r.get('tradeDate', '')
            if td:
                today = td[:10]
                break
        if today:
            redis_setex('market:max_date', [{'tradeDate': today}], TTL_SHORT)
            print(f'  max_date: {today}')
            total += 1
    else:
        print('  ** tencent_quote CSV 不存在！stock_basic & detail 写入跳过 **')

    # ════════════════════════════════════════════
    # 2. 指数
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
                'open_point': r.get('open', '0'),
                'high_point': r.get('high', '0'),
                'low_point': r.get('low', '0'),
                'volume': r.get('volume', '0'),
                'amount': r.get('amount', '0'),
                'pre_close': r.get('pre_close', r.get('yest_close', '0')),
            })
        cnt = safe_write_force_price('market:index_list', idx_list)
        print(f'  index_list: {len(idx_list)} (TTL={TTL_SHORT}s, force refresh)')
        total += cnt
    else:
        print('  ** tencent_index CSV 不存在！index_list 写入跳过 **')

    # ── 指数价格修正：用 K 线收盘价覆盖 CSV 数据 ──
    # CSV 可能滞后（例如 5/30 CSV 只有 5/29 收盘），K 线数据确保最新
    index_codes = [i.get('index_code','') for i in idx] if idx else []
    if index_codes:
        corrected = 0
        for ic in index_codes:
            if not ic:
                continue
            kline_raw = _redis_get(f'market:index_kline_{ic}')
            if kline_raw and isinstance(kline_raw, list) and len(kline_raw) > 0:
                latest = kline_raw[0]  # 降序，第一条最新
                close_val = latest.get('closePoint')
                trade_date = latest.get('tradeDate', '')
                if close_val and trade_date:
                    # 在 idx_list 中找到对应条目并更新价格
                    for entry in idx_list:
                        if entry.get('index_code') == ic:
                            old_price = entry.get('close_point', '?')
                            entry['close_point'] = close_val
                            # 重新计算 change_pct
                            entry['change_pct'] = latest.get('changePct', entry.get('change_pct', 0))
                            entry['open_point'] = latest.get('openPoint', entry.get('open_point', 0))
                            entry['high_point'] = latest.get('highPoint', entry.get('high_point', 0))
                            entry['low_point'] = latest.get('lowPoint', entry.get('low_point', 0))
                            corrected += 1
                            break
        if corrected > 0:
            # 用修正后的数据重写 index_list
            cnt2 = redis_setex('market:index_list', to_camel(idx_list), TTL_SHORT)
            print(f'  index_list: 通过 K 线修正 {corrected}/{len(index_codes)} 个指数价格 ✅')
            total += cnt2

    # ════════════════════════════════════════════
    # 3. 行业 + 北向 + 题材 + 新闻 + 基金
    # ════════════════════════════════════════════
    ind = latest_csv('industry_compare_*.csv')
    if ind:
        seen = set()
        ind_comp = []
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

        treemap = [{'industry': x['industry'], 'change_pct': x['change_pct'],
                     'mcap_yi': 0, 'stocks': x['stock_count']} for x in ind_comp]
        safe_write('market:industry_treemap', treemap, TTL_LONG)
        print(f'  industry_treemap: {len(treemap)}')
        total += len(treemap)
    else:
        print('  ** industry_compare CSV 不存在！行业数据跳过 **')

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
        print('  ** northbound CSV 不存在 **')

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
        print('  ** hot_reason CSV 不存在 **')

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
        print('  ** cls_news CSV 不存在 **')

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
        print('  ** global_news CSV 不存在 **')

    # ════════════════════════════════════════════
    # 8. 基金
    # ════════════════════════════════════════════
    fb = latest_csv('fund_basic_*.csv')
    if fb:
        fund_list = []
        for r in fb:
            code = r.get('fund_code', '')
            if not code:
                continue
            fund_list.append({
                'fundCode': code, 'fundName': r.get('fund_name', ''),
                'fundType': r.get('fund_type', ''), 'company': r.get('company', ''),
                'manager': r.get('manager', ''), 'establishDate': r.get('establish_date', ''),
                'nav': float(r.get('nav', 0)) if r.get('nav') else 0,
                'accumulatedNav': float(r.get('accumulated_nav', 0)) if r.get('accumulated_nav') else 0,
                'scale': float(r.get('scale', 0)) if r.get('scale') else 0,
                'fund_code': code, 'fund_name': r.get('fund_name', ''),
                'fund_type': r.get('fund_type', ''), 'establish_date': r.get('establish_date', ''),
                'accumulated_nav': float(r.get('accumulated_nav', 0)) if r.get('accumulated_nav') else 0,
            })
        safe_write_no_skip('market:fund_list', fund_list, TTL_LONG)
        print(f'  fund_list: {len(fund_list)}')
        total += len(fund_list)
    else:
        print('  ** fund_basic CSV 不存在 **')

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

    return total

def _kline_needs_refresh():
    """检查 K 线是否需要刷新（仅检查标杆股票 000001）"""
    ttl = _redis_ttl('market:kline_000001')
    return ttl < 600 or ttl == -2  # 剩余 <10min 或不存在


def _refresh_kline():
    """增量刷新 K 线数据（通过 subprocess 调用 seed_kline.py）"""
    if not _kline_needs_refresh():
        return 0
    print(f'[{datetime.now():%H:%M:%S}] K线数据需要刷新, 启动 seed_kline...')
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable, '/app/seed_kline.py'],
            timeout=3600, capture_output=True, text=True)
        if r.returncode == 0:
            lines = [l for l in r.stdout.split('\n') if '✅' in l or '❌' in l]
            for l in lines[-3:]:
                print(f'  {l}')
            print(f'  ✅ K线刷新完成')
        else:
            print(f'  ❌ K线刷新失败: {r.stderr[-200:]}')
    except subprocess.TimeoutExpired:
        print(f'  ⚠️ K线刷新超时(3600s)')


def seed_all():
    """全量填充（含 K 线刷新）"""
    print(f'[{datetime.now():%H:%M:%S}] 数据自愈管道启动 (socket 模式)...')
    t0 = time.time()
    total = fill_static()
    # K 线刷新（仅在 TTL 低时触发，白天交易时段一般跳过）
    _refresh_kline()
    elapsed = time.time() - t0
    key_count = _redis_cmd('DBSIZE')
    print(f'[{datetime.now():%H:%M:%S}] 完成! {total} 条, 耗时{elapsed:.0f}s, Redis共{key_count}key')
    return total

if __name__ == '__main__':
    print('=== 数据管道 (redis-cli 自愈) ===')
    seed_all()
    while True:
        try:
            time.sleep(1200)
            seed_all()
        except Exception as e:
            print(f'[{datetime.now():%H:%M:%S}] 管道异常(20分钟后重试): {e}')
            time.sleep(1200)
