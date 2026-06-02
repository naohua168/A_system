"""
CSV → HDFS 上传脚本 (WebHDFS REST API, 纯 urllib, 零外部依赖)

用法:
    python hdfs_upload.py                           # 上传最新 CSV
    python hdfs_upload.py --all                     # 上传所有 CSV
    python hdfs_upload.py --file /data/raw/xxx.csv  # 上传指定文件
"""
import os, sys, glob, json, urllib.request, urllib.error, time
from datetime import datetime

NAMENODE_HOST = 'namenode'
WEBHDFS_PORT = 9870
HDFS_BASE = '/data/stock/csv'
CSV_DIR = '/data/raw'

HEADERS = {'User-Agent': 'Mozilla/5.0'}


def _webhdfs_url(path):
    return f'http://{NAMENODE_HOST}:{WEBHDFS_PORT}/webhdfs/v1{HDFS_BASE}/{path.lstrip("/")}'


def _http_put(url, data=None):
    """HTTP PUT 请求"""
    req = urllib.request.Request(url, data=data or b'', method='PUT', headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')


def upload_file(local_path: str) -> bool:
    """通过 WebHDFS 上传单个文件到 HDFS"""
    filename = os.path.basename(local_path)
    if not os.path.isfile(local_path):
        print(f'  ⚠️ 文件不存在: {local_path}')
        return False

    # Step 1: 发起 CREATE 请求，获取重定向地址
    create_url = _webhdfs_url(filename) + '?op=CREATE&overwrite=true'
    status, body = _http_put(create_url)
    if status != 307:
        print(f'  ❌ WebHDFS CREATE 失败 (HTTP {status}): {body[:200]}')
        return False

    # Step 2: 从 Location 获取实际上传地址
    redirect_url = None
    try:
        req = urllib.request.Request(create_url, method='PUT', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            redirect_url = resp.headers.get('Location')
    except urllib.error.HTTPError as e:
        redirect_url = e.headers.get('Location') if hasattr(e, 'headers') else None
    except Exception:
        pass

    if not redirect_url:
        print(f'  ❌ 无法获取上传重定向地址')
        return False

    # Step 3: 上传文件内容
    with open(local_path, 'rb') as f:
        file_data = f.read()
    try:
        req2 = urllib.request.Request(redirect_url, data=file_data, method='PUT', headers=HEADERS)
        with urllib.request.urlopen(req2, timeout=60) as resp2:
            if resp2.status in (200, 201):
                size_mb = len(file_data) / 1024 / 1024
                print(f'  ✅ {filename} → hdfs://{HDFS_BASE}/{filename} ({size_mb:.1f}MB)')
                return True
            else:
                print(f'  ❌ 上传失败 (HTTP {resp2.status})')
                return False
    except urllib.error.HTTPError as e:
        print(f'  ❌ 上传失败 (HTTP {e.code}): {e.read().decode(errors="replace")[:200]}')
        return False
    except Exception as e:
        print(f'  ❌ 上传异常: {e}')
        return False


def upload_latest(pattern: str = None):
    """上传最新匹配的 CSV 文件"""
    if pattern is None:
        patterns = ['tencent_quote_*.csv', 'tencent_index_*.csv',
                     'realtime_*.csv', 'northbound_*.csv',
                     'industry_compare_*.csv', 'sector_ranking_*.csv',
                     'hot_reason_*.csv', 'kline_*.csv']
    else:
        patterns = [pattern] if isinstance(pattern, str) else pattern

    total = 0
    for p in patterns:
        files = sorted(glob.glob(os.path.join(CSV_DIR, p)))
        if files:
            if upload_file(files[-1]):
                total += 1
    return total


def upload_all():
    """上传所有 CSV 文件到 HDFS"""
    files = sorted(glob.glob(os.path.join(CSV_DIR, '*.csv')))
    success = 0
    for fp in files:
        if upload_file(fp):
            success += 1
    print(f'\n总计: {success}/{len(files)} 个文件上传成功')
    return success


if __name__ == '__main__':
    if '--all' in sys.argv:
        upload_all()
    elif '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            upload_file(sys.argv[idx + 1])
    else:
        upload_latest()
