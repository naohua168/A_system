"""
数据层管道 — 收盘快照模式 (纯 socket 实现, 零外部依赖)
交易日 15:00 后运行一次，全量采集写入 Redis (TTL=24h) + MySQL
新闻数据单独线程持续实时刷新
"""
import sys, json, csv, glob, os, re, time, socket, subprocess, urllib.request, urllib.parse, threading
from datetime import datetime

CSV_DIR = '/data/raw'
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# ── TTL 策略 ──
# 价格/涨跌幅数据必须短 TTL + no_skip，确保每次 auto_seed 运行都能刷新
# 静态基础数据可以长 TTL + skip，减少不必要写入
TTL_LONG = 604800       # 7 天（基础数据：行业、基金、指数列表）
TTL_MEDIUM = 86400      # 24 小时（动态数据：信号、资讯）
TTL_SHORT = 86400       # 24 小时（收盘快照模式：每日15:00后刷新一次，存到次日收盘）

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
            market_map = {'0': 'sz', '3': 'sz', '6': 'sh'}  # 0=深主板, 3=创业板, 6=沪主板
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
    _ensure_news_data()


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
        with open(fp, 'w', newline='', encoding='utf-8') as f:
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
    """龙虎榜：东方财富数据中心接口直取（最近5个交易日）"""
    if _csv_is_fresh('dragon_tiger_*.csv', _market_hours_max_age(7200)):
        return
    from datetime import date as _d, timedelta
    today = _d.today()
    # 生成最近5个交易日（不含今日，可能跨周末）
    target_dates = [today]
    for i in range(1, 8):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # 周一至周五
            target_dates.append(d)
        if len(target_dates) >= 5:
            break
    print(f'  [{datetime.now():%H:%M:%S}] 龙虎榜 CSV 过期，从 EastMoney API 直取 {len(target_dates)} 天...')
    try:
        all_rows = []
        for td in target_dates:
            ds = td.strftime('%Y-%m-%d')
            filter_enc = urllib.parse.quote(f"(TRADE_DATE>='{ds}')(TRADE_DATE<='{ds}')")
            url = ('https://datacenter-web.eastmoney.com/api/data/v1/get'
                   f'?reportName=RPT_DAILYBILLBOARD_DETAILSNEW'
                   f'&columns=ALL&pageSize=500'
                   f'&sortColumns=BILLBOARD_NET_AMT&sortTypes=-1'
                   f'&filter={filter_enc}')
            try:
                d = _fetch_json(url, EASTMONEY_HEADERS)
                items = d.get('result', {}).get('data', [])
                for item in items:
                    reason = item.get('BILLBOARD_REASON', '') or item.get('BOARD_REASON', '') or ''
                    net_buy = item.get('BILLBOARD_NET_AMT', 0) or 0
                    change = item.get('CHANGE_RATE', 0) or 0
                    turnover = item.get('TURNOVERRATE', 0) or 0
                    buy_amt = item.get('BILLBOARD_BUY_AMT', 0) or 0
                    sell_amt = item.get('BILLBOARD_SELL_AMT', 0) or 0
                    all_rows.append({
                        'stock_code': item.get('SECURITY_CODE', ''),
                        'stock_name': item.get('SECURITY_NAME_ABBR', ''),
                        'reason': reason,
                        'net_buy_wan': str(net_buy),
                        'change_pct': str(change),
                        'turnover_pct': str(turnover),
                        'buy_wan': str(buy_amt),
                        'sell_wan': str(sell_amt),
                        'trade_date': item.get('TRADE_DATE', ds)[:10],
                    })
                print(f'    {ds}: {len(items)} 条')
            except Exception as e:
                print(f'    {ds}: 失败 {e}')
                continue
        if not all_rows:
            print('  ⚠️ 多天龙虎榜均返回空')
            return
        fp = os.path.join(CSV_DIR, f'dragon_tiger_{datetime.now():%Y%m%d_%H%M%S}.csv')
        with open(fp, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['stock_code', 'stock_name', 'reason', 'net_buy_wan', 'change_pct',
                          'turnover_pct', 'buy_wan', 'sell_wan', 'trade_date']
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader(); w.writerows(all_rows)
        os.chmod(fp, 0o644)
        # 统计各日期条数
        from collections import Counter
        date_counts = Counter(r['trade_date'] for r in all_rows)
        detail = ', '.join(f'{d}:{c}' for d, c in sorted(date_counts.items()))
        print(f'  ✅ 龙虎榜 CSV 刷新: {os.path.basename(fp)} ({len(all_rows)} 条) [{detail}]')
    except Exception as e:
        print(f'  ❌ 龙虎榜直取失败: {e}')


# ════════════════════════════════════════════════
# 全球资讯数据获取（东方财富 np-weblist 7×24 快讯）
# ════════════════════════════════════════════════
EM_NEWS_HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://kuaixun.eastmoney.com/'}

def _ensure_news_data():
    """从东方财富获取全球资讯，直接写入 Redis market:global_news 和 market:cls_news"""
    import uuid
    try:
        url = 'https://np-weblist.eastmoney.com/comm/web/getFastNewsList'
        params = {
            'client': 'web', 'biz': 'web_724', 'fastColumn': '102',
            'sortEnd': '', 'pageSize': '100',
            'req_trace': str(uuid.uuid4()),
        }
        req = urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers=EM_NEWS_HEADERS)
        resp = urllib.request.urlopen(req, timeout=15)
        d = json.loads(resp.read().decode())
        raw_list = d.get('data', {}).get('fastNewsList', [])
        if not raw_list:
            print(f'  [{datetime.now():%H:%M:%S}] ⚠️ 东财全球资讯返回空')
            return

        # 转换格式: 源数据 {title, summary, showTime}
        seen = set()
        global_list = []
        cls_list = []
        news_id = 0
        for item in raw_list:
            title = (item.get('title') or '').strip()
            if not title or title in seen:
                continue
            seen.add(title)
            news_id += 1
            summary = (item.get('summary') or '')[:300]
            show_time = (item.get('showTime') or '')
            # showTime 格式如 "06-03 14:30"，补全年份
            if show_time and not show_time.startswith('20'):
                show_time = datetime.now().strftime('%Y-') + show_time
            # 提取新闻链接（如有）
            news_url = item.get('url') or item.get('sourceUrl') or item.get('articleUrl') or ''

            global_list.append({
                'title': title,
                'summary': summary,
                'publishTime': show_time,
                'source': '东方财富',
                'url': news_url,
                'id': news_id,
            })
            cls_list.append({
                'title': title,
                'content': summary,
                'datetime': show_time,
                'source': '东方财富',
                'id': 10000 + news_id,
            })

        # 写入 Redis
        if global_list:
            safe_write_no_skip('market:global_news', global_list, TTL_SHORT, 200)
        if cls_list:
            safe_write_no_skip('market:cls_news', cls_list, TTL_SHORT, 200)

        # ── 同时写入 MySQL info_news（新闻持久化，支持历史查询） ──
        try:
            import hashlib
            from datetime import datetime as _dt
            mysql_rows = []
            for item in global_list:
                news_id = hashlib.md5(item['title'].encode('utf-8')).hexdigest()[:16]
                pt = item.get('publishTime', '')
                try:
                    dt_val = _dt.strptime(pt, '%Y-%m-%d %H:%M') if pt and '-' in pt else _dt.now()
                except:
                    dt_val = _dt.now()
                mysql_rows.append((
                    news_id, item['title'][:500], item['summary'],
                    'global', dt_val, item['summary'], item['url'][:500],
                ))
            for item in cls_list:
                news_id = hashlib.md5(item['title'].encode('utf-8')).hexdigest()[:16]
                pt = item.get('datetime', '')
                try:
                    dt_val = _dt.strptime(pt, '%Y-%m-%d %H:%M') if pt and '-' in pt else _dt.now()
                except:
                    dt_val = _dt.now()
                mysql_rows.append((
                    news_id, item['title'][:500], item['content'],
                    'cls', dt_val, item['content'], '',
                ))
            if mysql_rows:
                import pymysql as _pm
                _conn = _pm.connect(host='mysql', port=3306, user='root',
                                    password='hadoop123', database='stock_history',
                                    charset='utf8mb4', connect_timeout=5)
                _cur = _conn.cursor()
                _sql = """INSERT IGNORE INTO info_news (news_id,title,summary,source,publish_time,content,url)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)"""
                _cur.executemany(_sql, mysql_rows)
                _conn.commit()
                _cur.close()
                _conn.close()
        except Exception as mysql_err:
            print(f'  [{datetime.now():%H:%M:%S}] ⚠️ 新闻写MySQL失败(不影响Redis): {mysql_err}')

        print(f'  [{datetime.now():%H:%M:%S}] ✅ 全球资讯刷新: {len(global_list)} 条 (TTL={TTL_SHORT}s)')
    except Exception as e:
        print(f'  [{datetime.now():%H:%M:%S}] ❌ 全球资讯直取失败: {e}')


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

def _redis_exists(key):
    """EXISTS key via socket"""
    resp = _redis_cmd('EXISTS', key)
    try:
        return int(resp) == 1
    except (ValueError, TypeError):
        return False

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


# ── 行业树图成分股增强 ──────────────────────────────────────────

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

    # ── 全球资讯直取刷新（短 TTL，必须每次刷新）──
    _ensure_news_data()

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

        # ── 用K线验证并修正 stock_basic 价格 ──
        # 抽样检查前50只，若偏差>5%的股票超过10%，则全量修正
        corrected_count = 0
        sample_size = min(50, len(sb_list))
        mismatches = 0
        for entry in sb_list[:sample_size]:
            code = entry.get('stock_code', '')
            if not code:
                continue
            kdata = _redis_get(f'market:kline_{code}')
            if kdata and isinstance(kdata, list) and len(kdata) > 0:
                kl_close = float(kdata[0].get('closePrice', 0))
                sb_price = float(entry.get('price', 0))
                if sb_price > 0 and kl_close > 0:
                    diff = abs(kl_close - sb_price) / max(sb_price, kl_close)
                    if diff > 0.05:
                        mismatches += 1
        if mismatches / sample_size > 0.10 and sample_size > 0:
            print(f'  ⚠️  stock_basic 与K线偏差较大 ({mismatches}/{sample_size}), 启动全量修正...')
            for entry in sb_list:
                code = entry.get('stock_code', '')
                if not code:
                    continue
                kdata = _redis_get(f'market:kline_{code}')
                if kdata and isinstance(kdata, list) and len(kdata) > 0:
                    kl = kdata[0]
                    kl_close = kl.get('closePrice')
                    if kl_close:
                        old_price = entry.get('price', '?')
                        entry['price'] = str(kl_close)
                        entry['change_pct'] = str(kl.get('changePct', entry.get('change_pct', '0')))
                        entry['last_close'] = str(kl.get('preClose', entry.get('last_close', '0')))
                        corrected_count += 1
            if corrected_count > 0:
                cnt2 = safe_write_force_price('market:stock_basic', sb_list)
                print(f'  ✅ stock_basic: K线修正 {corrected_count} 只股票 ✅')
        else:
            print(f'  stock_basic: K线验证通过 ({sample_size}抽检, {mismatches}偏差)')

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
    # 2. 指数 — 优先从 K 线获取最新数据，CSV 兜底
    # ════════════════════════════════════════════
    INDEX_CODES = ['000001', '399001', '399006', '000688', '000300']
    INDEX_NAMES = {'000001': '上证指数', '399001': '深证成指', '399006': '创业板指',
                   '000688': '科创50', '000300': '沪深300'}
    idx_list = []
    idx_from_kline = 0
    for ic in INDEX_CODES:
        kline_raw = _redis_get(f'market:index_kline_{ic}')
        if kline_raw and isinstance(kline_raw, list) and len(kline_raw) > 0:
            latest = kline_raw[0]  # 降序第一条最新
            prev_close = None
            if len(kline_raw) >= 2:
                prev_close = kline_raw[1].get('closePoint')
            idx_list.append({
                'index_code': ic,
                'index_name': INDEX_NAMES.get(ic, ''),
                'close_point': latest.get('closePoint', 0),
                'change_pct': latest.get('changePct', 0),
                'open_point': latest.get('openPoint', 0),
                'high_point': latest.get('highPoint', 0),
                'low_point': latest.get('lowPoint', 0),
                'volume': latest.get('volume', 0),
                'amount': latest.get('amount', 0),
                'pre_close': prev_close if prev_close else latest.get('closePoint', 0),
            })
            idx_from_kline += 1
    if idx_list:
        cnt = safe_write_force_price('market:index_list', to_camel(idx_list))
        print(f'  index_list: {len(idx_list)} (from K-line, TTL={TTL_SHORT}s, force refresh)')
        total += cnt
    else:
        # K 线不可用 → CSV 兜底
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
            print(f'  index_list: {len(idx_list)} (from CSV fallback, TTL={TTL_SHORT}s)')
            total += cnt
        else:
            print('  ** index_list: 无 K 线数据且 CSV 不存在，跳过 **')

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
                'industryName': name,
                'changePct': r.get('change_pct', '0'),
                'stockCount': int(r.get('up_count', 0) or 0) + int(r.get('down_count', 0) or 0),
                'totalAmount': 0,
            })
        cnt = safe_write_no_skip('market:industry_compare', ind_comp, TTL_SHORT)
        print(f'  industry_compare: {len(ind_comp)} (TTL={TTL_SHORT}s)')
        total += cnt

        treemap = [{'industryName': x['industryName'], 'changePct': x['changePct'],
                     'mcapYi': 0, 'stockCount': x['stockCount']} for x in ind_comp]

        # 先写入基础 treemap（不含 children），不阻塞后续关键数据写入
        safe_write_no_skip('market:industry_treemap', treemap, TTL_SHORT)
        print(f'  industry_treemap: {len(treemap)} base (TTL={TTL_SHORT}s)')
        total += len(treemap)
    else:
        print('  ** industry_compare CSV 不存在！行业数据跳过 **')

    nb = latest_csv('northbound_*.csv')
    if nb:
        # hexin time 仅 HH:MM 格式，同一 CSV 内都是同一交易日
        # 取最后一条记录（15:00 收盘累计值）作为当日北向资金数据
        last_row = None
        csv_date = ''
        nb_files = sorted(glob.glob(os.path.join(CSV_DIR, 'northbound_*.csv')))
        if nb_files:
            try:
                csv_mtime = os.path.getmtime(nb_files[-1])
                csv_date = datetime.fromtimestamp(csv_mtime).strftime('%Y-%m-%d')
            except:
                csv_date = datetime.now().strftime('%Y-%m-%d')
        for r in nb:
            raw_time = r.get('time', '') or r.get('trade_date', '') or r.get('date', '')
            if not raw_time:
                continue
            # 只处理 HH:MM 格式的 intraday 数据，记录最后一条
            if re.match(r'^\d{1,2}:\d{2}$', raw_time):
                last_row = r  # 不断覆盖，最终保留最后一条（15:00）
            else:
                last_row = r  # 已有完整日期的直接使用
        if last_row and csv_date:
            uniq = [{'tradeDate': csv_date,
                     'hgtYi': float(last_row.get('hgt_yi', 0) or last_row.get('hgtYi', 0)),
                     'sgtYi': float(last_row.get('sgt_yi', 0) or last_row.get('sgtYi', 0))}]
            safe_write_no_skip('market:northbound', uniq, TTL_SHORT)
            print(f'  northbound: 1 (TTL={TTL_SHORT}s) date={csv_date} hgt={uniq[0]["hgtYi"]} sgt={uniq[0]["sgtYi"]}')
            total += 1
            # ── 分钟级时序（262 个点）写入独立 key ──
            # 收盘后 hexin API 变为累计值，用盘中 15:00 前最后一个 CSV
            minute_key = f'market:northbound_minute:{csv_date.replace("-", "")}'
            minute_rows = []
            now_h = datetime.now().hour
            if now_h >= 15 and nb_files:
                # 找 15:00 前生成的当天 CSV（原始数据正确）
                daytime_csv = None
                for f in reversed(nb_files):
                    fh = datetime.fromtimestamp(os.path.getmtime(f)).hour
                    if 9 <= fh <= 14 and csv_date in f:
                        daytime_csv = f
                        break
                if daytime_csv:
                    try:
                        with open(daytime_csv, 'r', encoding='utf-8') as f:
                            reader = list(csv.DictReader(f))
                            for r in reader:
                                t = r.get('time', '').strip()
                                if re.match(r'^\d{1,2}:\d{2}$', t):
                                    minute_rows.append({
                                        'time': t,
                                        'hgtYi': float(r.get('hgt_yi', 0) or r.get('hgtYi', 0)),
                                        'sgtYi': float(r.get('sgt_yi', 0) or r.get('sgtYi', 0)),
                                    })
                    except Exception:
                        minute_rows = []
            else:
                # 盘中：直接用最新 CSV
                for r in nb:
                    t = r.get('time', '').strip()
                    if re.match(r'^\d{1,2}:\d{2}$', t):
                        minute_rows.append({
                            'time': t,
                            'hgtYi': float(r.get('hgt_yi', 0) or r.get('hgtYi', 0)),
                            'sgtYi': float(r.get('sgt_yi', 0) or r.get('sgtYi', 0)),
                        })
            if minute_rows:
                safe_write_no_skip(minute_key, minute_rows, TTL_SHORT)
                print(f'  northbound_minute: {len(minute_rows)} 个时间点 key={minute_key}')
        else:
            print('  ** northbound: 无有效数据（跳过）**')
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
                uniq.append({'stockCode': c, 'stockName': r.get('名称',''),
                             'reason': r.get('题材归因',''), 'tradeDate': r.get('date','')})
        safe_write_no_skip('market:hot_reason', uniq, TTL_SHORT, 200)
        print(f'  hot_reason: {min(len(uniq),200)} (TTL={TTL_SHORT}s)')
        total += min(len(uniq), 200)
    else:
        print('  ** hot_reason CSV 不存在 **')

    # ── 龙虎榜 ──
    dt = latest_csv('dragon_tiger_*.csv')
    if dt:
        uniq = []
        for r in dt:
            code = r.get('stock_code', '')
            if code and code not in {x.get('stock_code','') for x in uniq}:
                uniq.append({
                    'stockCode': code,
                    'stockName': r.get('stock_name', ''),
                    'reason': str(r.get('reason', '')),
                    'netBuyWan': float(r.get('net_buy_wan', 0) or 0),
                    'changePct': float(r.get('change_pct', 0) or 0),
                    'turnoverPct': float(r.get('turnover_pct', 0) or 0),
                    'buyWan': float(r.get('buy_wan', 0) or 0),
                    'sellWan': float(r.get('sell_wan', 0) or 0),
                    'tradeDate': r.get('trade_date', ''),
                })
        safe_write_no_skip('market:dragon_tiger', uniq, TTL_SHORT)
        print(f'  dragon_tiger: {len(uniq)} (TTL={TTL_SHORT}s)')
        total += len(uniq)
    else:
        print('  ** dragon_tiger CSV 不存在 **')

    # ── 锁解汇总（聚合所有 lockup_* key → lockup_upcoming） ──
    try:
        subprocess.run(
            [sys.executable, '/app/al.py'],
            capture_output=True, timeout=120)
        print('  lockup_upcoming: 聚合刷新完成')
    except Exception as e:
        print(f'  lockup_upcoming 刷新失败: {e}')

    return total


def _kline_needs_refresh():
    """检查日K是否需要刷新"""
    ttl = _redis_ttl('market:kline_000001')
    return ttl < 3600  # 日K TTL < 1h 才刷新

def _min_kline_needs_refresh():
    """检查分钟K线是否需要刷新（独立检查，不受日K影响）"""
    ttl = _redis_ttl('market:kline_5min_000001')
    return ttl < 1800  # 分钟K线 TTL < 30min 则刷新


def _refresh_kline():
    """增量刷新 K 线数据（后台进程，不阻塞 auto_seed 主流程）"""
    import subprocess
    # ── 日K/周K/月K（只要日K TTL 低才刷新）──
    if _kline_needs_refresh():
        print(f'[{datetime.now():%H:%M:%S}] 日K TTL 低, 后台启动 seed_kline...')
        subprocess.Popen(
            [sys.executable, '/app/seed_kline.py'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f'  ✅ 日K刷新已启动')
    # ── 分钟K线（独立检查，不受日K影响）──
    if _min_kline_needs_refresh():
        for min_period in ['5min', '15min', '30min', '60min']:
            subprocess.Popen(
                [sys.executable, '/app/seed_kline.py', '--period', min_period],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f'  ✅ 分钟K线刷新已启动（5min/15min/30min/60min）')

def _repair_missing_kline():
    """检查并修复缺失的个股K线数据（每次 seed_all 轮询探测）"""
    try:
        raw = _redis_get('market:stock_basic')
        if not raw or not isinstance(raw, list):
            return
        # 取前20只股票检查K线覆盖率
        codes = [s.get('stockCode', '') or s.get('stock_code', '') for s in raw[:20]]
        codes = [c for c in codes if c]
        if not codes:
            return
        missing = sum(1 for c in codes if not _redis_exists(f'market:kline_{c}'))
        missing_pct = missing / len(codes)
        if missing_pct > 0.15:  # 缺失 > 15% → 启动后台全量采集
            print(f'  [{datetime.now():%H:%M:%S}] 缺失K线 {missing}/{len(codes)}, 启动后台 seed_kline...')
            import subprocess as _sp
            _sp.Popen([sys.executable, '/app/seed_kline.py'],
                      stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            print(f'  ✅ 日K全量刷新已启动（后台）')
        elif missing > 0:
            print(f'  kline: 缺失 {missing}/{len(codes)}（<15%，暂不触发）')
    except Exception:
        pass

def _rebuild_index_list():
    """从K线最新数据重新生成 index_list（K线刷新后调用）"""
    INDEX_CODES = ['000001', '399001', '399006', '000688', '000300']
    INDEX_NAMES = {'000001': '上证指数', '399001': '深证成指', '399006': '创业板指',
                   '000688': '科创50', '000300': '沪深300'}
    idx_list = []
    for ic in INDEX_CODES:
        kline_raw = _redis_get(f'market:index_kline_{ic}')
        if kline_raw and isinstance(kline_raw, list) and len(kline_raw) > 0:
            latest = kline_raw[0]
            prev_close = kline_raw[1].get('closePoint') if len(kline_raw) >= 2 else latest.get('closePoint')
            idx_list.append({
                'index_code': ic, 'index_name': INDEX_NAMES.get(ic, ''),
                'close_point': latest.get('closePoint', 0),
                'change_pct': latest.get('changePct', 0),
                'open_point': latest.get('openPoint', 0),
                'high_point': latest.get('highPoint', 0),
                'low_point': latest.get('lowPoint', 0),
                'volume': latest.get('volume', 0),
                'amount': latest.get('amount', 0),
                'pre_close': prev_close if prev_close else latest.get('closePoint', 0),
            })
    if idx_list:
        safe_write_force_price('market:index_list', to_camel(idx_list))
    return len(idx_list)


def data_rollover():
    """
    收盘快照 — 每日仅执行一次（交易日 15:00 后触发）

    Step 1: fill_static   → 行情+信号+资金流向+锁解（含csv直取）
    Step 2: seed_analysis → 涨跌排行衍生
    Step 3: K线刷新       → 日K+分钟K（后台Popen），随后重算指数
    Step 4: MySQL 归档    → 7张表日终快照
    """
    done_key = 'market:rollover_done_today'
    if _redis_exists(done_key):
        print(f'[{datetime.now():%H:%M:%S}] 今日 rollover 已完成，跳过')
        return 0

    print(f'[{datetime.now():%H:%M:%S}] ═══ 收盘快照启动 ═══')
    t0 = time.time()
    total = 0

    try:
        # ═══════════════════════════════════════════════
        # Step 1: fill_static — 行情+信号+资金流向+锁解
        # ═══════════════════════════════════════════════
        print(f'[{datetime.now():%H:%M:%S}] Step 1/4: 行情+信号...')
        total += fill_static()

        # ═══════════════════════════════════════════════
        # Step 2: 涨跌排行（fill_static 不包含此项）
        # ═══════════════════════════════════════════════
        print(f'[{datetime.now():%H:%M:%S}] Step 2/4: 涨跌排行...')
        try:
            import subprocess
            subprocess.run([sys.executable, '/app/seed_analysis.py'], capture_output=True, timeout=60)
            print('  rankings: 刷新完成')
        except Exception:
            pass

        # ═══════════════════════════════════════════════
        # Step 3: K线刷新（后台Popen）→ 重算指数
        # ═══════════════════════════════════════════════
        print(f'[{datetime.now():%H:%M:%S}] Step 3/4: K线+指数...')
        _repair_missing_kline()
        _refresh_kline()
        # K线刷新后立即重算指数（避免 fill_static 读到旧K线）
        idx_cnt = _rebuild_index_list()
        print(f'  index_list: {idx_cnt} (rebuilt after kline refresh)')
        total += idx_cnt

        # ═══════════════════════════════════════════════
        # Step 4: MySQL 归档（后台Popen）+ 设完成标志
        # ═══════════════════════════════════════════════
        print(f'[{datetime.now():%H:%M:%S}] Step 4/4: MySQL 归档...')
        now = datetime.now()
        if now.weekday() < 5 and now.hour >= 15:
            try:
                import subprocess
                subprocess.Popen(
                    [sys.executable, '/app/daily_snapshot_to_mysql.py'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print('  ✅ 日终快照已触发（后台写入 MySQL stock_history）')
            except Exception as e:
                print(f'  ⚠️ 日终快照失败: {e}')

        # ── 设完成标志（放最后，但被 try/except 兜底） ──
        _redis_setex(done_key, {'date': str(now.date()), 'time': str(now.time())[:8]}, TTL_MEDIUM)
        print(f'  ✅ rollover_done_today 已设置')

    except Exception as e:
        print(f'  ❌ rollover 异常: {e}')
        import traceback
        traceback.print_exc()
        err_time = datetime.now()
        _redis_setex(done_key, {'date': str(err_time.date()),
                                'time': str(err_time.time())[:8],
                                'error': str(e)[:100]}, TTL_MEDIUM)
        print(f'  ⚠️ 异常后已设置 rollover 标志（标注 error）')

    elapsed = time.time() - t0
    key_count = _redis_cmd('DBSIZE')
    print(f'[{datetime.now():%H:%M:%S}] ═══ 收盘快照完成 ═══ {total}条, {elapsed:.0f}s, Redis共{key_count}key')
    return total

def _news_refresh_loop():
    """新闻数据实时刷新 — 每 5 分钟采集一次（独立线程，不阻塞）"""
    while True:
        try:
            _ensure_news_data()
        except Exception:
            pass
        time.sleep(300)  # 5分钟

if __name__ == '__main__':
    print('=== 数据管道 (收盘快照模式) ===')
    # 1) 收盘快照：写入 Redis (TTL=24h) + MySQL 归档
    data_rollover()
    # 2) 启动新闻实时刷新线程（每5分钟，盘中/盘后持续）
    import threading
    news_thread = threading.Thread(target=_news_refresh_loop, daemon=True)
    news_thread.start()
    print(f'[{datetime.now():%H:%M:%S}] 新闻刷新线程已启动（每5分钟）')
    # 3) 主进程保持存活（供后台线程运行），不再循环 data_rollover
    while True:
        time.sleep(60)
