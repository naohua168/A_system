"""
数据层自愈管道 — CSV→Redis (纯 socket 实现, 零外部依赖)
每 20 分钟自动运行，确保所有 Redis key 不因 TTL 过期
"""
import sys, json, csv, glob, os, re, time, socket, urllib.request, urllib.parse, threading
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

TENCENT_QUOTE_COLS = [
    'stock_code', 'stock_name', 'price', 'last_close', 'open', 'volume',
    'change_amt', 'change_pct', 'high', 'low', 'amount_wan',
    'turnover_pct', 'pe_ttm', 'amplitude_pct', 'mcap_yi',
    'float_mcap_yi', 'pb', 'limit_up', 'limit_down', 'vol_ratio'
]

def _parse_tencent_quote(line: str):
    """解析腾讯行情接口返回的 v_xx="..."; 格式"""
    try:
        eq = line.index('=')
        raw = line[eq+2:-2]  # skip =" and ";
        parts = raw.split('~')
        if len(parts) < 46:
            return None
        code_full = parts[2]   # 如 sh000001, sz000001
        market = code_full[:2]
        code = code_full[2:] if market in ('sh','sz') else code_full
        name = parts[1]
        price = parts[3]       # 当前价
        last_close = parts[4]  # 昨收
        open_p = parts[5]      # 今开
        volume = parts[6]      # 成交量(手)
        high = parts[33]       # 最高
        low = parts[34]        # 最低
        change_pct = parts[32] # 涨跌幅%
        change_amt = parts[31] # 涨跌额
        amount = parts[37]     # 成交额(万)
        turnover = parts[38]   # 换手率%
        pe = parts[39]         # PE
        amplitude = parts[43]  # 振幅%
        mcap = parts[44]       # 总市值(万)
        float_mcap = parts[45] # 流通市值(万)
        pb = parts[46] if len(parts) > 46 else ''
        limit_up = parts[47] if len(parts) > 47 else ''
        limit_down = parts[48] if len(parts) > 48 else ''
        vol_ratio = parts[49] if len(parts) > 49 else ''
        return {
            'stock_code': code, 'stock_name': name, 'price': price,
            'last_close': last_close, 'open': open_p, 'volume': volume,
            'change_amt': change_amt, 'change_pct': change_pct,
            'high': high, 'low': low, 'amount_wan': amount,
            'turnover_pct': turnover, 'pe_ttm': pe,
            'amplitude_pct': amplitude, 'mcap_yi': mcap,
            'float_mcap_yi': float_mcap, 'pb': pb,
            'limit_up': limit_up, 'limit_down': limit_down,
            'vol_ratio': vol_ratio,
        }
    except (ValueError, IndexError):
        return None


def _fetch_tencent_quote(codes: list) -> list:
    """分批从腾讯 API 获取实时行情（100只/批, 20并发）"""
    BATCH = 100
    CONCURRENT = 20
    results = []
    lock = threading.Lock()
    headers = {'User-Agent': 'Mozilla/5.0'}

    def fetch_batch(batch_codes: list):
        nonlocal results
        try:
            market_map = {'0': 'sh', '3': 'sz', '6': 'sh'}  # 深市主板/创业板走sz
            qs = []
            for c in batch_codes:
                prefix = market_map.get(c[0], 'sz')
                qs.append(f'{prefix}{c}')
            url = 'https://web.sqt.gtimg.cn/q=' + ','.join(qs)
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=10).read().decode('gbk')
            for line in resp.strip().split('\n'):
                row = _parse_tencent_quote(line)
                if row:
                    with lock:
                        results.append(row)
        except Exception as e:
            pass  # 静默跳过失败的批次

    threads = []
    for i in range(0, len(codes), BATCH):
        batch = codes[i:i+BATCH]
        t = threading.Thread(target=fetch_batch, args=(batch,))
        threads.append(t)
        t.start()
        if len(threads) >= CONCURRENT:
            threads[0].join()
            threads.pop(0)
    for t in threads:
        t.join()
    return results


def _csv_is_fresh(pattern: str, max_age_sec=3600) -> bool:
    """检查最新 CSV 是否足够新鲜"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))
    if not files:
        return False
    age = time.time() - os.path.getmtime(files[-1])
    return age < max_age_sec


def _write_realtime_csv(rows: list, prefix='tencent_quote'):
    """写入实时行情 CSV"""
    if not rows:
        return None
    fp = os.path.join(CSV_DIR, f'{prefix}_{datetime.now():%Y%m%d_%H%M%S}.csv')
    with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=TENCENT_QUOTE_COLS)
        writer.writeheader()
        writer.writerows(rows)
    os.chmod(fp, 0o644)
    return fp


def _ensure_fresh_csv():
    """确保实时行情 CSV 是最新的（超过1小时则从腾讯API直取）"""
    # 交易时段(9:00-15:00) 10分钟刷新一次，非交易时段1小时
    h = datetime.now().hour
    is_market_hours = h in range(9, 15)
    max_age = 600 if is_market_hours else 3600  # 10min / 1h
    if _csv_is_fresh('tencent_quote_*.csv', max_age):
        return
    print(f'[{datetime.now():%H:%M:%S}] CSV 过期，从腾讯 API 直取实时行情...')
    # 从已有的 CSV 读取股票代码
    codes = _read_stock_codes_from_csv()
    if not codes:
        print('  ⚠️ 无法获取股票代码列表')
        return
    rows = _fetch_tencent_quote(codes)
    if rows:
        fp = _write_realtime_csv(rows)
        print(f'  ✅ 实时行情 CSV 已刷新: {os.path.basename(fp)} ({len(rows)} 只)')
    else:
        print('  ❌ 腾讯 API 实时行情获取失败')

    # ── 额外检查并刷新其他数据源 CSV ──
    _ensure_northbound_csv()
    _ensure_hot_reason_csv()
    _ensure_industry_compare_csv()
    _ensure_dragon_tiger_csv()


# ════════════════════════════════════════════════
# 数据源直取函数（绕过熔断器）
# ════════════════════════════════════════════════
EASTMONEY_HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://data.eastmoney.com/'}
HEXIN_HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://data.hexin.cn/'}
TENJQKA_HEADERS = {'User-Agent': 'Mozilla/5.0'}

def _fetch_json(url, headers, timeout=10):
    """GET JSON 辅助"""
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())


def _market_hours_max_age(normal_sec=7200):
    """交易时段用更短的刷新间隔"""
    h = datetime.now().hour
    if h in range(9, 16):  # 9:00-15:00
        return 600  # 10min
    return normal_sec

def _ensure_northbound_csv():
    """北向资金：同花顺 hexin 接口直取"""
    if _csv_is_fresh('northbound_*.csv', _market_hours_max_age(7200)):
        return
    print(f'  [{datetime.now():%H:%M:%S}] 北向资金 CSV 过期，从 hexin API 直取...')
    try:
        d = _fetch_json('https://data.hexin.cn/market/hsgtApi/method/dayChart/', HEXIN_HEADERS)
        times = d.get('time', [])
        hgt = d.get('hgt', [])
        sgt = d.get('sgt', [])
        if not times:
            print('  ⚠️ hexin 北向资金返回空')
            return
        rows = []
        for i in range(len(times)):
            rows.append({
                'time': str(times[i]),
                'hgt_yi': float(hgt[i]) if i < len(hgt) else 0.0,
                'sgt_yi': float(sgt[i]) if i < len(sgt) else 0.0,
                'source': 'hexin_api',
            })
        fp = os.path.join(CSV_DIR, f'northbound_{datetime.now():%Y%m%d_%H%M%S}.csv')
        with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['time', 'hgt_yi', 'sgt_yi', 'source'])
            w.writeheader(); w.writerows(rows)
        os.chmod(fp, 0o644)
        print(f'  ✅ 北向资金 CSV 刷新: {os.path.basename(fp)} ({len(rows)} 个时间点)')
    except Exception as e:
        print(f'  ❌ 北向资金直取失败: {e}')


def _ensure_hot_reason_csv():
    """题材热点：同花顺 10jqka 接口直取"""
    if _csv_is_fresh('hot_reason_*.csv', _market_hours_max_age(7200)):
        return
    from datetime import date as _d
    today_str = _d.today().strftime('%Y-%m-%d')
    print(f'  [{datetime.now():%H:%M:%S}] 题材热点 CSV 过期，从 10jqka API 直取...')
    try:
        url = f'http://zx.10jqka.com.cn/event/api/getharden/date/{today_str}/orderby/date/orderway/desc/charset/GBK/'
        req = urllib.request.Request(url, headers=TENJQKA_HEADERS)
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode('gbk')
        d = json.loads(raw)
        data_list = d.get('data', [])
        if not data_list:
            print('  ⚠️ 10jqka 题材热点返回空')
            return
        rows = []
        for item in data_list:
            rows.append({
                'id': str(item.get('id', '')),
                '名称': item.get('name', ''),
                '代码': item.get('code', ''),
                '题材归因': item.get('reason', ''),
                'date': today_str,
                '市场': str(item.get('market', '')),
                'source': '10jqka_api',
                'fetch_date': today_str,
            })
        fp = os.path.join(CSV_DIR, f'hot_reason_{datetime.now():%Y%m%d_%H%M%S}.csv')
        with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['id', '名称', '代码', '题材归因', 'date', '市场', 'source', 'fetch_date'])
            w.writeheader(); w.writerows(rows)
        os.chmod(fp, 0o644)
        print(f'  ✅ 题材热点 CSV 刷新: {os.path.basename(fp)} ({len(rows)} 只)')
    except Exception as e:
        print(f'  ❌ 题材热点直取失败: {e}')


def _ensure_industry_compare_csv():
    """行业对比：尝试多个 API 直取，全部失败则保留缓存"""
    if _csv_is_fresh('industry_compare_*.csv', _market_hours_max_age(7200)):
        return
    print(f'  [{datetime.now():%H:%M:%S}] 行业对比 CSV 过期，尝试 API 直取...')
    rows = None

    # 方案1: 东方财富推送API (push2, 容器网络可能不可用)
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&fields=f12,f14,f3,f62,f184,f66&fid=f3&fs=m:90+t:2'
        d = _fetch_json(url, EASTMONEY_HEADERS)
        items = d.get('data', {}).get('diff', [])
        if items:
            rows = []
            for item in items:
                cp = 0.0
                try: cp = float(item.get('f3', 0))
                except: pass
                rows.append({
                    'industry': item.get('f14', ''),
                    'code': item.get('f12', ''),
                    'change_pct': str(cp),
                    'up_count': str(item.get('f184', 0)),
                    'down_count': str(int(item.get('f66', 0) or 0) - int(item.get('f184', 0) or 0)),
                })
    except Exception:
        pass

    # 方案2: 腾讯板块API (通过已知行业代码)
    if not rows:
        try:
            import csv as _csv
            old_files = sorted(glob.glob(os.path.join(CSV_DIR, 'industry_compare_*.csv')))
            if old_files:
                codes = []
                with open(old_files[-1], 'r', encoding='utf-8-sig') as f:
                    reader = _csv.DictReader(f)
                    for row in reader:
                        c = row.get('code', '').strip()
                        if c:
                            codes.append(c)
                if codes:
                    rows2 = []
                    for i in range(0, len(codes), 50):
                        batch = codes[i:i+50]
                        qs = [f'sh{c}' if not c.startswith(('sh','sz')) else c for c in batch]
                        url = 'https://web.sqt.gtimg.cn/q=' + ','.join(qs)
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        resp = urllib.request.urlopen(req, timeout=10)
                        content = resp.read().decode('gbk', errors='replace')
                        for line in content.strip().split('\n'):
                            match = re.search(r'v_\w+="(.*)"', line)
                            if match:
                                parts = match.group(1).split('~')
                                if len(parts) > 3 and parts[1]:
                                    code_full = parts[2]
                                    name = parts[1]
                                    price = parts[3]
                                    change = parts[32] if len(parts) > 32 else '0'
                                    try:
                                        rows2.append({
                                            'industry': name,
                                            'code': code_full,
                                            'change_pct': str(float(change)),
                                            'up_count': '0',
                                            'down_count': '0',
                                        })
                                    except: pass
                    if rows2:
                        rows = rows2
        except Exception:
            pass

    # 方案3+4: 融合申万行业 + 东方财富板块（去重合并）
    try:
        import akshare as ak
        merged = []

        # 3. 申万行业（基础）
        try:
            df_sw = ak.stock_sector_spot()
            if not df_sw.empty:
                for _, row in df_sw.iterrows():
                    name = str(row.get('板块', '')).strip()
                    pct = float(row.get('涨跌幅', 0) or 0)
                    if name:
                        merged.append({
                            'industry': name, 'code': '',
                            'change_pct': str(round(pct, 2)),
                            'up_count': '0', 'down_count': '0',
                        })
        except:
            pass

        # 4. 东方财富全板块（补充分支行业，去重）
        try:
            df_em = ak.stock_board_change_em()
            if not df_em.empty:
                exist_names = {r['industry'] for r in merged}
                skip_kw = ['融资', '通股', '概念', '昨日', '活跃', '首板', '次新', '北向', '富时', '转债', 'ETF']
                added = 0
                for _, row in df_em.iterrows():
                    name = str(row.get('板块名称', '')).strip()
                    pct = float(row.get('涨跌幅', 0) or 0)
                    if name and pct != 0 and name not in exist_names and not any(kw in name for kw in skip_kw):
                        merged.append({
                            'industry': name, 'code': '',
                            'change_pct': str(round(pct, 2)),
                            'up_count': '0', 'down_count': '0',
                        })
                        added += 1
                        if added >= 50:  # 最多补充50个分支行业
                            break
        except:
            pass

        if merged:
            rows = merged
            print(f'  ✅ akshare 融合行业: 申万{len([r for r in merged if r["industry"] in exist_names])} + 东方财富{len([r for r in merged if r["industry"] not in exist_names])} = {len(merged)} 个')
    except ImportError:
        print('  ⚠️ akshare 未安装，跳过')
    except Exception:
        pass

    if rows:
        fp = os.path.join(CSV_DIR, f'industry_compare_{datetime.now():%Y%m%d_%H%M%S}.csv')
        with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['industry', 'code', 'change_pct', 'up_count', 'down_count'])
            w.writeheader(); w.writerows(rows)
        os.chmod(fp, 0o644)
        print(f'  ✅ 行业对比 CSV 刷新: {os.path.basename(fp)} ({len(rows)} 个行业)')
    else:
        print(f'  ⚠️ 所有 API 失败，保留缓存行业数据')


def _ensure_dragon_tiger_csv():
    """龙虎榜：东方财富数据中心接口直取"""
    if _csv_is_fresh('dragon_tiger_*.csv', _market_hours_max_age(7200)):
        return
    from datetime import date as _d
    today_str = _d.today().strftime('%Y-%m-%d')
    print(f'  [{datetime.now():%H:%M:%S}] 龙虎榜 CSV 过期，从 EastMoney API 直取...')
    try:
        filter_enc = urllib.parse.quote(f"(TRADE_DATE>='{today_str}')(TRADE_DATE<='{today_str}')")
        url = ('https://datacenter-web.eastmoney.com/api/data/v1/get'
               f'?reportName=RPT_DAILYBILLBOARD_DETAILSNEW'
               f'&columns=ALL&pageSize=500'
               f'&sortColumns=BILLBOARD_NET_AMT&sortTypes=-1'
               f'&filter={filter_enc}')
        d = _fetch_json(url, EASTMONEY_HEADERS)
        items = d.get('result', {}).get('data', [])
        if not items:
            print('  ⚠️ EastMoney 龙虎榜返回空')
            return
        rows = []
        for item in items:
            # 东方财富龙虎榜字段：BILLBOARD_REASON=上榜原因, BILLBOARD_NET_AMT=净买入额
            reason = item.get('BILLBOARD_REASON', '') or item.get('BOARD_REASON', '') or ''
            net_buy = item.get('BILLBOARD_NET_AMT', 0) or 0
            change = item.get('CHANGE_PCT', 0) or 0
            rows.append({
                'stock_code': item.get('SECURITY_CODE', ''),
                'stock_name': item.get('SECURITY_NAME_ABBR', ''),
                'reason': reason,
                'net_buy_wan': str(net_buy),
                'change_pct': str(change),
                'trade_date': today_str,
            })
        fp = os.path.join(CSV_DIR, f'dragon_tiger_{datetime.now():%Y%m%d_%H%M%S}.csv')
        with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=['stock_code', 'stock_name', 'reason', 'net_buy_wan', 'change_pct', 'trade_date'])
            w.writeheader(); w.writerows(rows)
        os.chmod(fp, 0o644)
        print(f'  ✅ 龙虎榜 CSV 刷新: {os.path.basename(fp)} ({len(rows)} 条)')
    except Exception as e:
        print(f'  ❌ 龙虎榜直取失败: {e}')


def _read_stock_codes_from_csv() -> list:
    """从最新的 CSV 读取股票代码"""
    patterns = ['realtime_*.csv', 'tencent_quote_*.csv', 'stock_basic_*.csv']
    for p in patterns:
        files = sorted(glob.glob(os.path.join(CSV_DIR, p)))
        if files:
            with open(files[-1], 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                codes = []
                for row in reader:
                    code = (row.get('stock_code') or row.get('code') or '').strip()
                    if code:
                        codes.append(code)
                return codes
    return []


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
    return resp.endswith('OK')  # RESP 响应为 +OK\r\n → 处理后为 +OK，检查后缀

def _redis_ttl(key):
    """TTL key via socket"""
    resp = _redis_cmd('TTL', key)
    try:
        return int(resp)
    except (ValueError, TypeError):
        return -2

def _redis_get(key):
    """GET key via socket, returns parsed JSON or None
    使用长度前缀精确读取，避免 JSON 内容中的 \\r\\n 污染 RESP 解析"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((REDIS_HOST, REDIS_PORT))
        # 用 bytes 拼接 CRLF，避免 escape 混淆
        cmd = b'*2\r\n$3\r\nGET\r\n$' + str(len(key)).encode() + b'\r\n' + key.encode() + b'\r\n'
        s.sendall(cmd)
        # 读取响应头: $<len>\r\n
        header = b''
        while True:
            ch = s.recv(1)
            if not ch:
                s.close(); return None
            header += ch
            if header.endswith(b'\r\n'):
                break
        if header.startswith(b'$-1'):
            s.close(); return None  # nil
        if header[0:1] != b'$':
            s.close(); return None
        # 提取长度
        payload_len = int(header[1:-2])  # strip $ and \r\n
        # 按精确长度读取
        payload = b''
        remaining = payload_len
        while remaining > 0:
            chunk = s.recv(min(remaining, 65536))
            if not chunk:
                break
            payload += chunk
            remaining -= len(chunk)
        s.close()
        if not payload:
            return None
        return json.loads(payload.decode('utf-8'))
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

    # ── 确保实时行情 CSV 是最新的 ──
    _ensure_fresh_csv()

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

        # market:stats — 全市场涨跌统计（前端首页卡片用）
        try:
            up_cnt = sum(1 for r in tq if r.get('change_pct') and float(r['change_pct']) > 0)
            down_cnt = sum(1 for r in tq if r.get('change_pct') and float(r['change_pct']) < 0)
            flat_cnt = sum(1 for r in tq if not r.get('change_pct') or float(r['change_pct']) == 0)
            stats = {'total': len(tq), 'up': up_cnt, 'down': down_cnt, 'flat': flat_cnt}
            safe_write_no_skip('market:stats', stats, TTL_SHORT)
            print(f'  stats: 总{stats["total"]} 涨{stats["up"]} 跌{stats["down"]} 平{stats["flat"]}')
            total += 1
        except:
            pass

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
        for ic_raw in index_codes:
            if not ic_raw:
                continue
            # CSV index_code 带 sh/sz 前缀（如 sh000001），K 线 key 无前缀
            ic = ic_raw
            for p in ('sh', 'sz', 'SH', 'SZ'):
                if ic.startswith(p):
                    ic = ic[len(p):]
                    break
            kline_raw = _redis_get(f'market:index_kline_{ic}')
            if kline_raw and isinstance(kline_raw, list) and len(kline_raw) > 0:
                latest = kline_raw[0]  # 降序，第一条最新
                close_val = latest.get('closePoint')
                trade_date = latest.get('tradeDate', '')
                if close_val and trade_date:
                    # 在 idx_list 中找到对应条目并更新价格（idx_list 已去前缀，用 ic 匹配）
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
        cnt = safe_write_no_skip('market:industry_compare', ind_comp, TTL_SHORT)
        print(f'  industry_compare: {len(ind_comp)} (TTL={TTL_SHORT}s)')
        total += cnt

        treemap = [{'industry': x['industry'], 'change_pct': x['change_pct'],
                     'mcap_yi': 0, 'stocks': x['stock_count']} for x in ind_comp]
        safe_write_no_skip('market:industry_treemap', treemap, TTL_SHORT)
        print(f'  industry_treemap: {len(treemap)} (TTL={TTL_SHORT}s)')
        total += len(treemap)
    else:
        print('  ** industry_compare CSV 不存在！行业数据跳过 **')

    nb = latest_csv('northbound_*.csv')
    if nb:
        seen = set()
        uniq = []
        for r in nb:
            # CSV 字段可能是 time 或 trade_date（不同采集器版本）
            d = r.get('time', '') or r.get('trade_date', '') or r.get('date', '')
            if d not in seen and d:
                seen.add(d)
                uniq.append({'trade_date': d, 'hgt_yi': r.get('hgt_yi','0'), 'sgt_yi': r.get('sgt_yi','0')})
        safe_write_no_skip('market:northbound', uniq[-50:], TTL_SHORT, 50)
        print(f'  northbound: {min(len(uniq),50)} (TTL={TTL_SHORT}s)')
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
        safe_write_no_skip('market:hot_reason', uniq, TTL_SHORT, 200)
        print(f'  hot_reason: {min(len(uniq),200)} (TTL={TTL_SHORT}s)')
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

    # ── 龙虎榜 ──
    dt = latest_csv('dragon_tiger_*.csv')
    if dt:
        uniq = []
        for r in dt:
            code = r.get('stock_code', '')
            if code and code not in {x.get('stock_code','') for x in uniq}:
                uniq.append({
                    'stock_code': code,
                    'stock_name': r.get('stock_name', ''),
                    'reason': str(r.get('reason', '')),
                    'change_pct': r.get('change_pct', 0),
                    'trade_date': r.get('trade_date', ''),
                })
        safe_write_no_skip('market:dragon_tiger', uniq, TTL_SHORT)
        print(f'  dragon_tiger: {len(uniq)} (TTL={TTL_SHORT}s)')
        total += len(uniq)
    else:
        print('  ** dragon_tiger CSV 不存在 **')

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
    """检查 K 线是否需要刷新（仅当 TTL 极低时，避免阻塞 auto_seed）"""
    ttl = _redis_ttl('market:kline_000001')
    return ttl < 60  # 仅剩 <1min 才刷新


def _refresh_kline():
    """增量刷新 K 线数据（后台进程，不阻塞 auto_seed 主流程）"""
    if not _kline_needs_refresh():
        return 0
    print(f'[{datetime.now():%H:%M:%S}] K线 TTL 低, 后台启动 seed_kline...')
    import subprocess
    subprocess.Popen(
        [sys.executable, '/app/seed_kline.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'  ✅ K线刷新已在后台启动')


def seed_all():
    """全量填充（含 K 线刷新 + HDFS 备份）"""
    print(f'[{datetime.now():%H:%M:%S}] 数据自愈管道启动 (socket 模式)...')
    t0 = time.time()
    total = fill_static()
    # K 线刷新（仅在 TTL 低时触发，白天交易时段一般跳过）
    _refresh_kline()
    # CSV → HDFS 数据湖备份（不阻塞主流程）
    try:
        from hdfs_upload import upload_latest
        upload_latest()
    except Exception:
        pass
    # HDFS 分析结果 → Redis（Spark 批处理产出）
    try:
        from hdfs_to_redis import sync_analysis_to_redis
        sync_analysis_to_redis()
    except Exception:
        pass
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
