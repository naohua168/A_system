"""
日终快照：从 Redis 读取当日数据 → 写入 MySQL stock_history
交易日 15:00 后执行一次，全量归档当日市场快照

用法:
    python daily_snapshot_to_mysql.py
"""
import json, socket
from datetime import date, datetime

REDIS_HOST = 'redis'
REDIS_PORT = 6379
MYSQL_HOST = 'mysql'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASS = 'hadoop123'
MYSQL_DB = 'stock_history'
TODAY = date.today()
TODAY_STR = TODAY.strftime('%Y-%m-%d')

# ── Redis 读取（纯 socket RESP）──

def _redis_cmd(*args):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((REDIS_HOST, REDIS_PORT))
    buf = '*%d\r\n' % len(args)
    for a in args:
        a = str(a).encode('utf-8')
        buf += '$%d\r\n%s\r\n' % (len(a), a.decode())
    s.sendall(buf.encode())
    resp = b''
    while True:
        try:
            chunk = s.recv(65536)
            if not chunk: break
            resp += chunk
        except socket.timeout: break
    s.close()
    return resp.decode()

def _redis_get(key):
    raw = _redis_cmd('GET', key)
    if not raw or raw.startswith('$-1') or raw.startswith('*-1'):
        return None
    try:
        bulk = raw.split('\r\n', 1)[1] if '\r\n' in raw else raw
        return json.loads(bulk.strip())
    except Exception:
        return None

# ── MySQL 写入（pymysql）──

def _get_mysql_conn():
    import pymysql
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset='utf8mb4',
        connect_timeout=10, autocommit=False
    )

def _executemany(sql, rows):
    """批量写入"""
    if not rows:
        print('    无数据，跳过')
        return True
    try:
        conn = _get_mysql_conn()
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f'    ❌ MySQL 写入失败: {e}')
        return False

def _clear_today(table):
    """清空今日数据（用于无唯一键约束的表，避免重复）"""
    try:
        conn = _get_mysql_conn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table} WHERE trade_date=%s", (TODAY_STR,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f'    ⚠️  清空{table}失败: {e}')

# ── 各表快照 ──

def save_stock_daily():
    print('  [stock_daily] 读取 Redis...')
    data = _redis_get('market:stock_basic')
    if not data or not isinstance(data, list):
        print('  ⚠️  无数据，跳过'); return 0
    rows = []
    for s in data:
        code = s.get('stockCode') or s.get('stock_code', '')
        name = s.get('stockName') or s.get('stock_name', '')
        try:
            close_p = float(s.get('price', 0) or 0)
            open_p = float(s.get('open', 0) or s.get('lastClose', 0) or s.get('last_close', 0) or 0)
            high_p = float(s.get('high', 0) or close_p)
            low_p = float(s.get('low', 0) or close_p)
            vol = int(float(s.get('volume', 0) or 0))
            cp = float(s.get('changePct', 0) or s.get('change_pct', 0) or 0)
            tp = float(s.get('turnoverPct', 0) or s.get('turnover_pct', 0) or 0)
            pe = float(s.get('peTtm', 0) or s.get('pe_ttm', 0) or 0)
            pb = float(s.get('pb', 0) or 0)
            mcap = float(s.get('mcapYi', 0) or s.get('mcap_yi', 0) or 0)
        except (ValueError, TypeError):
            continue
        rows.append((TODAY_STR, code, name,
                     open_p, close_p, high_p, low_p, vol, cp, tp, pe, pb, mcap))

    # 过滤空代码行
    rows = [r for r in rows if r[1]]
    if not rows:
        print('  ⚠️  无有效数据，跳过'); return 0
    sql = """INSERT INTO stock_daily
             (trade_date,stock_code,stock_name,open_price,close_price,high_price,low_price,volume,change_pct,turnover_pct,pe_ttm,pb,mcap_yi)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE close_price=VALUES(close_price),change_pct=VALUES(change_pct),turnover_pct=VALUES(turnover_pct)"""
    ok = _executemany(sql, rows)
    print(f'  [stock_daily] {len(rows)} 行 {"✅" if ok else "❌"}')
    return len(rows)

def save_index_daily():
    print('  [index_daily] 读取 Redis...')
    data = _redis_get('market:index_list')
    if not data or not isinstance(data, list):
        print('  ⚠️  无数据，跳过'); return 0
    rows = [(TODAY_STR,
             idx.get('indexCode','') or idx.get('index_code',''), idx.get('indexName','') or idx.get('index_name',''),
             float(idx.get('closePoint',0)or 0), float(idx.get('changePct',0)or 0),
             float(idx.get('openPoint',0)or 0), float(idx.get('highPoint',0)or 0),
             float(idx.get('lowPoint',0)or 0), int(float(idx.get('volume',0)or 0)),
             float(idx.get('preClose',0)or 0))
            for idx in data]
    sql = """INSERT INTO index_daily (trade_date,index_code,index_name,close_point,change_pct,open_point,high_point,low_point,volume,pre_close)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE close_point=VALUES(close_point),change_pct=VALUES(change_pct)"""
    ok = _executemany(sql, rows)
    print(f'  [index_daily] {len(rows)} 行 {"✅" if ok else "❌"}')
    return len(rows)

def save_industry_daily():
    print('  [industry_daily] 读取 Redis...')
    data = _redis_get('market:industry_compare')
    if not data or not isinstance(data, list):
        print('  ⚠️  无数据，跳过'); return 0
    rows = [(TODAY_STR, ind.get('industryName',''),
             float(ind.get('changePct',0)or 0),
             int(ind.get('stockCount',0)or 0),
             float(ind.get('totalAmount',0)or 0))
            for ind in data]
    sql = "INSERT INTO industry_daily (trade_date,industry_name,change_pct,stock_count,total_amount) VALUES (%s,%s,%s,%s,%s)"
    _clear_today('industry_daily')
    ok = _executemany(sql, rows)
    print(f'  [industry_daily] {len(rows)} 行 {"✅" if ok else "❌"}')
    return len(rows)

def save_northbound():
    print('  [northbound_daily] 读取 Redis...')
    data = _redis_get('market:northbound')
    if not data or not isinstance(data, list) or len(data) == 0:
        print('  ⚠️  无数据，跳过'); return 0
    item = data[0]
    hgt = float(item.get('hgtYi', 0) or 0)
    sgt = float(item.get('sgtYi', 0) or 0)
    if hgt == 0 and sgt == 0:
        print('  ⚠️  全零，跳过'); return 0
    sql = "INSERT INTO northbound_daily (trade_date,hgt_yi,sgt_yi) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE hgt_yi=VALUES(hgt_yi),sgt_yi=VALUES(sgt_yi)"
    ok = _executemany(sql, [(TODAY_STR, hgt, sgt)])
    print(f'  [northbound_daily] 1 行 (hgt={hgt}, sgt={sgt}) {"✅" if ok else "❌"}')
    return 1

def save_hot_reason():
    print('  [hot_reason_daily] 读取 Redis...')
    data = _redis_get('market:hot_reason')
    if not data or not isinstance(data, list):
        print('  ⚠️  无数据，跳过'); return 0
    rows = []
    for h in data:
        code = h.get('stockCode') or h.get('stock_code', '')
        name = h.get('stockName') or h.get('stock_name', '')
        reason = h.get('reason', '')
        if not code:
            continue
        rows.append((TODAY_STR, code, name, reason))
    sql = "INSERT INTO hot_reason_daily (trade_date,stock_code,stock_name,reason) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE reason=VALUES(reason)"
    _clear_today('hot_reason_daily')
    ok = _executemany(sql, rows)
    print(f'  [hot_reason_daily] {len(rows)} 行 {"✅" if ok else "❌"}')
    return len(rows)

def save_dragon_tiger():
    print('  [dragon_tiger_daily] 读取 Redis...')
    data = _redis_get('market:dragon_tiger')
    if not data or not isinstance(data, list):
        print('  ⚠️  无数据，跳过'); return 0
    rows = []
    for dt in data:
        code = dt.get('stockCode') or dt.get('stock_code', '')
        name = dt.get('stockName') or dt.get('stock_name', '')
        reason = dt.get('reason', '')
        if not code:
            continue
        net_buy = float(dt.get('netBuyWan', 0) or dt.get('net_buy_wan', 0) or 0)
        cp = float(dt.get('changePct', 0) or dt.get('change_pct', 0) or 0)
        tp = float(dt.get('turnoverPct', 0) or dt.get('turnover_pct', 0) or 0)
        buy = float(dt.get('buyWan', 0) or dt.get('buy_wan', 0) or 0)
        sell = float(dt.get('sellWan', 0) or dt.get('sell_wan', 0) or 0)
        rows.append((TODAY_STR, code, name, reason, net_buy, cp, tp, buy, sell))
    sql = """INSERT INTO dragon_tiger_daily (trade_date,stock_code,stock_name,reason,net_buy_wan,change_pct,turnover_pct,buy_wan,sell_wan)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
             ON DUPLICATE KEY UPDATE net_buy_wan=VALUES(net_buy_wan),change_pct=VALUES(change_pct)"""
    _clear_today('dragon_tiger_daily')
    ok = _executemany(sql, rows)
    print(f'  [dragon_tiger_daily] {len(rows)} 行 {"✅" if ok else "❌"}')
    return len(rows)

def main():
    print(f'\n{"="*50}')
    print(f'📦 日终快照 [{datetime.now():%Y-%m-%d %H:%M:%S}]')
    print(f'   数据库: {MYSQL_DB}, 交易日: {TODAY_STR}')
    print(f'{"="*50}\n')
    total = 0
    total += save_stock_daily()
    total += save_index_daily()
    total += save_industry_daily()
    total += save_northbound()
    total += save_hot_reason()
    total += save_dragon_tiger()
    print(f'\n{"="*50}')
    print(f'🏁 日终快照完成: 共 {total} 行')
    print(f'{"="*50}')
    return total

if __name__ == '__main__':
    main()
