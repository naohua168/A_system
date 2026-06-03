"""
K线数据 seed 管道 — 腾讯API → Redis (纯 socket 实现, 零外部依赖)
从腾讯财经采集日K线数据，写入 Redis
支持指数K线和个股K线
"""
import sys, json, time, glob, os, csv, re, socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Redis 连接 ──
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# ── TTL 策略 ──
TTL_INDEX = 86400     # 指数K线 24h (MEDIUM)
TTL_STOCK = 43200     # 个股K线 12h (比实时行情长，比指数短)

# ── 采集参数 ──
MAX_WORKERS = 20
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
TENCENT_API = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},{period},,,{count},qfq'

# 支持的多周期（腾讯API：day/week/month/m5/m15/m30/m60）
PERIODS = {
    'day':   {'param': 'day',   'count': 365,  'ttl': TTL_STOCK},
    'week':  {'param': 'week',  'count': 120,  'ttl': 86400 * 2},
    'month': {'param': 'month', 'count': 60,   'ttl': 86400 * 7},
    '5min':  {'param': 'm5',    'count': 30,   'ttl': 3600},
    '15min': {'param': 'm15',   'count': 30,   'ttl': 3600},
    '30min': {'param': 'm30',   'count': 30,   'ttl': 3600},
    '60min': {'param': 'm60',   'count': 30,   'ttl': 3600},
}

INDICES = ['000001', '399001', '399006', '000688', '000300']
CSV_DIR = '/data/raw'


# ════════════════════════════════════════════
# 1. Redis socket 操作 (纯 RESP 协议)
# ════════════════════════════════════════════

def _redis_cmd(*args):
    """发送 Redis RESP 命令，返回响应字符串"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((REDIS_HOST, REDIS_PORT))
        parts = [b'*' + str(len(args)).encode()]
        for a in args:
            ab = a.encode('utf-8') if isinstance(a, str) else a
            parts.append(b'$' + str(len(ab)).encode())
            parts.append(ab)
        s.sendall(b'\r\n'.join(parts) + b'\r\n')
        s.settimeout(5)
        data = b''
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        s.close()
        result = data.decode('utf-8', errors='replace').strip()
        if result.startswith('+') or result.startswith(':'):
            return result[1:]
        if result == '+OK' or result == 'OK':
            return 'OK'
        return result
    except Exception as e:
        return f'-ERR:{e}'


def redis_setex(key, value, ttl):
    """SETEX key ttl value"""
    js = json.dumps(value, ensure_ascii=False, default=str)
    resp = _redis_cmd('SETEX', key, str(ttl), js)
    return resp == 'OK'


# ════════════════════════════════════════════
# 2. K线数据获取
# ════════════════════════════════════════════

def get_prefix(code, is_index=False):
    """代码前缀"""
    if is_index:
        return 'sh' if code.startswith(('0', '6', '9')) else 'sz'
    if code.startswith(('6', '9')):
        return 'sh'
    elif code.startswith(('0', '1', '2', '3')):
        return 'sz'
    elif code.startswith('8'):
        return 'bj'
    return 'sz'


def fetch_kline(code, is_index=False, period='day'):
    """获取单只股票/指数的K线（支持多周期：day/week/month/5min/15min/30min/60min）"""
    p = PERIODS.get(period, PERIODS['day'])
    prefix = get_prefix(code, is_index)
    url = TENCENT_API.format(prefix=prefix, code=code, period=p['param'], count=p['count'])
    try:
        req = Request(url, headers={'User-Agent': UA})
        with urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read().decode('utf-8'))
    except (URLError, json.JSONDecodeError, OSError):
        return None

    data = d.get('data', {})
    record = data.get(code) or data.get(prefix + code) or {}
    # 日K/周K/月K用 qfqday，分钟K线用 m5/m15/m30/m60
    period_key = p['param']
    minute_keys = {'m5', 'm15', 'm30', 'm60'}
    if period_key in minute_keys:
        # 分钟K线用独立 endpoint: /appstock/app/kline/mkline
        minute_url = f'https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={prefix}{code},{period_key},,{p["count"]}'
        try:
            req2 = Request(minute_url, headers={'User-Agent': UA})
            with urlopen(req2, timeout=15) as resp2:
                d2 = json.loads(resp2.read().decode('utf-8'))
            rec2 = d2.get('data', {}).get(prefix + code) or d2.get('data', {}).get(code) or {}
            klines = rec2.get(period_key) or []
        except Exception:
            klines = []
    elif period_key == 'day':
        klines = record.get('qfqday') or record.get('day') or data.get('qt', {}).get(code, {}).get('day') or data.get('qt', {}).get(code, {}).get('qfqday') or []
    else:
        # week/month 可能在 record 顶层
        klines = record.get(period_key) or []
    if not klines:
        return None

    rows = []
    for k in klines:
        if len(k) < 6:
            continue
        try:
            trade_date = k[0].replace('-', '')
            o = float(k[1])
            c = float(k[2])
            h = float(k[3])
            l_ = float(k[4])
            v = int(float(k[5])) if isinstance(k[5], (int, float, str)) and str(k[5]).strip() else 0
            a = float(k[6]) if len(k) > 6 and isinstance(k[6], (int, float, str)) and str(k[6]).strip() else 0
            change_pct = round((c - o) / o * 100, 2) if o > 0 else 0
        except (ValueError, TypeError, IndexError):
            continue

        if is_index:
            row = {
                'indexCode': code,
                'tradeDate': trade_date,
                'openPoint': o,
                'closePoint': c,
                'highPoint': h,
                'lowPoint': l_,
                'volume': v,
                'amount': a,
                'changePct': change_pct,
            }
        else:
            row = {
                'stockCode': code,
                'tradeDate': trade_date,
                'openPrice': o,
                'closePrice': c,
                'highPrice': h,
                'lowPrice': l_,
                'volume': v,
                'amount': a,
                'changePct': change_pct,
                'preClose': o,
                'turnoverRate': 0,
            }
        rows.append(row)

    # 降序 (最新在前)
    rows.reverse()
    return rows


# ════════════════════════════════════════════
# 3. 批量采集
# ════════════════════════════════════════════

def read_stock_codes():
    """从 CSV 读取股票代码列表"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, 'realtime_*.csv')))
    if not files:
        files = sorted(glob.glob(os.path.join(CSV_DIR, 'tencent_quote_*.csv')))
    if not files:
        files = sorted(glob.glob(os.path.join(CSV_DIR, 'stock_basic_*.csv')))
    if not files:
        print('ERROR: 找不到股票列表 CSV')
        return []

    print(f'  CSV: {os.path.basename(files[-1])}')
    codes = []
    with open(files[-1], 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get('stock_code') or row.get('code') or '').strip()
            if code:
                codes.append(code)
    return codes


def collect_indices(period='day'):
    """采集指数K线（支持多周期）"""
    p = PERIODS.get(period, PERIODS['day'])
    label = f'指数K线({period})' if period != 'day' else '指数K线'
    print(f'[{datetime.now():%H:%M:%S}] 采集{label}...')
    total = 0
    for code in INDICES:
        klines = fetch_kline(code, is_index=True, period=period)
        if klines:
            key = f'market:index_kline_{period}_{code}' if period != 'day' else f'market:index_kline_{code}'
            ok = redis_setex(key, klines, p['ttl'])
            n = len(klines)
            print(f'  指数 {code}: {n}条 {"✅" if ok else "❌"}')
            total += n
        else:
            print(f'  指数 {code}: 采集失败')
        time.sleep(0.3)
    return total


def collect_one_stock(code, period='day'):
    """采集单只个股K线（支持多周期）"""
    p = PERIODS.get(period, PERIODS['day'])
    klines = fetch_kline(code, is_index=False, period=period)
    if not klines:
        return code, 0
    key = f'market:kline_{period}_{code}' if period != 'day' else f'market:kline_{code}'
    ok = redis_setex(key, klines, p['ttl'])
    return code, len(klines) if ok else 0


def collect_stocks(codes, period='day'):
    """并发采集所有个股K线（支持多周期）"""
    label = f'个股K线({period})' if period != 'day' else '个股K线'
    print(f'[{datetime.now():%H:%M:%S}] 采集{label}...')
    total = 0
    success = 0
    done = 0
    n_codes = len(codes)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(collect_one_stock, code, period): code for code in codes}
        for future in as_completed(futures):
            code, n = future.result()
            done += 1
            if n > 0:
                total += n
                success += 1
            if done % 500 == 0 or done == n_codes:
                elapsed = time.time() - t0
                print(f'  [{datetime.now():%H:%M:%S}] {done}/{n_codes}, 成功:{success} 条数:{total} 耗时:{elapsed:.0f}s')

    return total, success


# ════════════════════════════════════════════
# 4. 主入口
# ════════════════════════════════════════════

def seed_kline(period='day'):
    """全量 K 线 seed 入口（支持多周期）"""
    global t0
    t0 = time.time()
    period_label = {'day':'日K', 'week':'周K', 'month':'月K', '5min':'5分钟', '15min':'15分钟', '30min':'30分钟', '60min':'60分钟'}
    label = period_label.get(period, period)
    print(f'=== K线数据 Seed 启动 [{datetime.now():%H:%M:%S}] ===')
    print(f'周期: {label}')

    # 1. 指数K线
    idx_count = collect_indices(period)
    print(f'✅ 指数K线({period}): {idx_count}条')

    # 2. 个股K线
    codes = read_stock_codes()
    if not codes:
        print('❌ 无股票列表，退出')
        return

    print(f'  共 {len(codes)} 只股票')
    stock_total, stock_ok = collect_stocks(codes, period)
    elapsed = time.time() - t0

    print(f'\n{"="*50}')
    print(f'✅ 个股K线({period}): {stock_total}条, 成功{stock_ok}/{len(codes)}只')
    print(f'⏱ 总耗时: {elapsed:.0f}s')
    print(f'{"="*50}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='K线数据采集')
    parser.add_argument('--period', default='day', choices=list(PERIODS.keys()),
                        help='K线周期: day/week/month/5min/15min/30min/60min')
    args = parser.parse_args()
    seed_kline(args.period)
