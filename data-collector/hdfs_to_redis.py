"""
HDFS 分析结果 → Redis 管道 (WebHDFS + socket RESP, 零外部依赖)

读取 Spark 写入 HDFS 的 JSON 分析结果，推入 Redis，
供后端 API 直接读取。
"""
import os, sys, json, socket, urllib.request, re
from datetime import datetime

NAMENODE = 'namenode'
WEBHDFS_PORT = 9870
ANALYSIS_BASE = '/data/stock/analysis'
REDIS_HOST = 'redis'
REDIS_PORT = 6379

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Redis key 映射：分析类型 → Redis key
REDIS_KEY_MAP = {
    'top_gainers': 'market:analysis:top_gainers',
    'top_losers': 'market:analysis:top_losers',
    'high_volume': 'market:analysis:high_volume',
}


def _webhdfs(path):
    return f'http://{NAMENODE}:{WEBHDFS_PORT}/webhdfs/v1{path}'


def _http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _redis_setex(key, value, ttl=3600):
    """socket RESP SETEX — 使用字节长度避免中文截断"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((REDIS_HOST, REDIS_PORT))
        payload = json.dumps(value, ensure_ascii=False, default=str)
        payload_bytes = payload.encode('utf-8')
        key_bytes = key.encode()
        ttl_str = str(ttl)
        # RESP: *4\r\n$5\r\nSETEX\r\n$K\r\nKEY\r\n$T\r\nTTL\r\n$P\r\nPAYLOAD\r\n
        parts = [
            f'*4\r\n$5\r\nSETEX\r\n'.encode(),
            f'${len(key_bytes)}\r\n'.encode(), key_bytes, b'\r\n',
            f'${len(ttl_str)}\r\n'.encode(), ttl_str.encode(), b'\r\n',
            f'${len(payload_bytes)}\r\n'.encode(), payload_bytes, b'\r\n',
        ]
        s.sendall(b''.join(parts))
        s.settimeout(3)
        resp = b''
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk: break
                resp += chunk
            except socket.timeout:
                break
        s.close()
        return resp.decode().strip() in ('+OK', 'OK')
    except Exception:
        return False


def _list_analysis_dirs():
    """列出所有分析子目录"""
    url = _webhdfs(ANALYSIS_BASE) + '?op=LISTSTATUS'
    status, data = _http_get(url)
    if status != 200:
        return []
    fs = json.loads(data.decode()).get('FileStatuses', {}).get('FileStatus', [])
    return [f['pathSuffix'] for f in fs if f['type'] == 'DIRECTORY']


def _get_latest_json(analysis_type: str):
    """获取指定分析类型的最新 JSON 文件内容"""
    dir_url = _webhdfs(f'{ANALYSIS_BASE}/{analysis_type}/_out') + '?op=LISTSTATUS'
    status, data = _http_get(dir_url)
    if status != 200:
        return None
    files = json.loads(data.decode()).get('FileStatuses', {}).get('FileStatus', [])
    json_files = [f for f in files if f['pathSuffix'].endswith('.json') and not f['pathSuffix'].startswith('.')]
    if not json_files:
        return None
    # 取最新的 JSON 文件
    latest = max(json_files, key=lambda f: f['modificationTime'])
    file_url = _webhdfs(f'{ANALYSIS_BASE}/{analysis_type}/_out/{latest["pathSuffix"]}') + '?op=OPEN'
    # urllib 自动处理重定向
    try:
        req = urllib.request.Request(file_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            records = [json.loads(line) for line in content.strip().split('\n') if line.strip()]
            return records
    except Exception as e:
        print(f'  ⚠️ 读取 {analysis_type} 失败: {e}')
        return None


def sync_analysis_to_redis():
    """同步所有分析结果到 Redis"""
    total = 0
    for analysis_type, redis_key in REDIS_KEY_MAP.items():
        records = _get_latest_json(analysis_type)
        if not records:
            continue
        ok = _redis_setex(redis_key, records)
        if ok:
            print(f'  ✅ {analysis_type}: {len(records)} 条 → {redis_key}')
            total += 1
        else:
            print(f'  ❌ {analysis_type}: Redis 写入失败')
    return total


if __name__ == '__main__':
    print(f'[{datetime.now():%H:%M:%S}] HDFS→Redis 分析管道启动...')
    cnt = sync_analysis_to_redis()
    print(f'[{datetime.now():%H:%M:%S}] 完成: {cnt} 个分析结果同步')
