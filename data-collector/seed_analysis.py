#!/usr/bin/env python3
"""从 stock_basic 生成个股涨跌排行 —— Redis socket 直连"""
import json, socket, sys, time

REDIS_HOST = 'redis'
REDIS_PORT = 6379

def _redis_cmd(*args):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15)
        s.connect((REDIS_HOST, REDIS_PORT))
        # RESP array
        buf = f'*{len(args)}\r\n'.encode()
        for a in args:
            a_bytes = str(a).encode('utf-8')
            buf += f'${len(a_bytes)}\r\n'.encode() + a_bytes + b'\r\n'
        s.sendall(buf)
        # read response - bulk string
        data = b''
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
            if data.startswith(b'$'):
                # $<len>\r\n<data>\r\n
                parts = data.split(b'\r\n', 2)
                if len(parts) >= 3:
                    return parts[1]
            elif data.startswith(b'+') or data.startswith(b':'):
                return data[1:].strip()
            elif data.startswith(b'-'):
                return None
        return data
    except Exception as e:
        print(f'  Redis error: {e}')
        return None
    finally:
        try:
            s.close()
        except:
            pass

def main():
    t0 = time.time()
    raw = _redis_cmd('GET', 'market:stock_basic')
    if not raw:
        print('ERROR: market:stock_basic not found')
        sys.exit(1)
    try:
        stocks = json.loads(raw) if isinstance(raw, (str, bytes)) else json.loads(raw.decode())
    except Exception as e:
        print(f'ERROR parse: {e}')
        if isinstance(raw, bytes):
            try: stocks = json.loads(raw.decode())
            except: sys.exit(1)
        else:
            sys.exit(1)
    if isinstance(stocks, str):
        try: stocks = json.loads(stocks)
        except: pass
    if not isinstance(stocks, list):
        print(f'ERROR: not list but {type(stocks).__name__}')
        sys.exit(1)
    print(f'Read {len(stocks)} stocks')

    valid = [s for s in stocks if s.get('changePct') is not None and s.get('price') is not None]
    print(f'Valid: {len(valid)}')

    top_gainers = sorted(valid, key=lambda x: -(x.get('changePct') or 0))[:100]
    top_losers = sorted(valid, key=lambda x: (x.get('changePct') or 0))[:100]
    high_volume = sorted(valid, key=lambda x: -(x.get('turnoverPct') or 0))[:100]

    for key, data in [('market:analysis:top_gainers', top_gainers),
                      ('market:analysis:top_losers', top_losers),
                      ('market:analysis:high_volume', high_volume)]:
        dump = json.dumps(data, ensure_ascii=False)
        r = _redis_cmd('SET', key, dump)
        _redis_cmd('EXPIRE', key, 3600)  # 1h TTL，配合每分钟刷新
        print(f'SET {key}: {len(data)} → {r}')

    print(f'Done in {time.time()-t0:.1f}s')

if __name__ == '__main__':
    main()
