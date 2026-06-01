"""
从 K-line CSV 文件写入 Redis — 用于 run_collector scheduler 的收尾步骤
读取 scheduler 生成的 kline_{code}.csv 文件，写入 Redis market:kline_{code}
使用 socket RESP 协议，零外部依赖
"""
import json, csv, glob, os, time, socket, sys

CSV_DIR = '/data/raw'
REDIS_HOST = 'redis'
REDIS_PORT = 6379
TTL = 604800  # 7 days
BATCH_SIZE = 500  # flush log every N stocks

def redis_set(key, val, ttl):
    js = json.dumps(val, ensure_ascii=False, default=str)
    s = socket.socket(); s.settimeout(10)
    s.connect((REDIS_HOST, REDIS_PORT))
    lines = [b'*4', b'$5', b'SETEX', b'$' + str(len(key)).encode(), key.encode(),
             b'$' + str(len(str(ttl))).encode(), str(ttl).encode(),
             b'$' + str(len(js)).encode(), js.encode()]
    s.sendall(b'\r\n'.join(lines) + b'\r\n')
    s.settimeout(3)
    try: s.recv(1024)
    except: pass
    s.close()

def main():
    t0 = time.time()
    # Find all kline CSV files
    files = sorted(glob.glob(os.path.join(CSV_DIR, 'kline_*.csv')))
    print(f'Found {len(files)} kline CSV files')
    
    # Extract unique stock codes
    codes = set()
    for f in files:
        base = os.path.basename(f)
        # kline_{code}.csv
        code = base[len('kline_'):-4]
        codes.add(code)
    print(f'Unique stock codes: {len(codes)}')
    
    total = 0; success = 0
    for i, code in enumerate(sorted(codes)):
        csv_file = os.path.join(CSV_DIR, f'kline_{code}.csv')
        if not os.path.exists(csv_file):
            continue
        try:
            rows = []
            with open(csv_file, encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    # Normalize field names from various CSV formats
                    try:
                        td = row.get('trade_date','') or row.get('date','') or row.get('tradeDate','')
                        td = td.replace('-','')
                        o = float(row.get('open_price','') or row.get('open','') or 0)
                        h = float(row.get('high_price','') or row.get('high','') or 0)
                        l = float(row.get('low_price','') or row.get('low','') or 0)
                        c = float(row.get('close_price','') or row.get('close','') or 0)
                        v = int(float(row.get('volume','') or 0))
                        a = float(row.get('amount','') or 0)
                        cp = float(row.get('change_percent','') or row.get('change_pct','') or 0)
                        pc = float(row.get('pre_close','') or row.get('preClose','') or 0)
                        tr = float(row.get('turnover_rate','') or row.get('turnoverRate','') or 0)
                        rows.append({
                            'stockCode': code, 'tradeDate': td,
                            'openPrice': o, 'closePrice': c,
                            'highPrice': h, 'lowPrice': l,
                            'volume': v, 'amount': a,
                            'changePct': cp, 'preClose': pc, 'turnoverRate': tr,
                        })
                    except (ValueError, TypeError):
                        continue
            if len(rows) >= 10:
                rows.sort(key=lambda x: x['tradeDate'])  # asc
                rows.reverse()  # latest first
                redis_set(f'market:kline_{code}', rows, TTL)
                total += len(rows)
                success += 1
        except Exception as e:
            print(f'  ERROR {code}: {e}')
        
        if (i + 1) % BATCH_SIZE == 0:
            elapsed = time.time() - t0
            print(f'  {i+1}/{len(codes)} success={success} klines={total} {elapsed:.0f}s')
    
    elapsed = time.time() - t0
    print(f'DONE: {success}/{len(codes)} stocks, {total} klines, {elapsed:.0f}s')

if __name__ == '__main__':
    main()
