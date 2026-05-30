"""
WebHDFS 文件上传 — 将 /data/raw/ 下的 CSV 上传到 HDFS
使用 HTTP PUT 直接通过 WebHDFS API（无需 hdfs 库）
"""
import os, sys, json, time, logging, re
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, HDFS as HDFS_CFG

logger = logging.getLogger('hdfs_uploader')

# 文件前缀 → HDFS 子目录
ROUTES = {
    'kline_': '/user/hadoop/stock_data/daily',
    'realtime_': '/user/hadoop/stock_data/realtime',
    'stock_basic': '/user/hadoop/stock_data/basic',
    'hot_reason': '/user/hadoop/stock_data/signals/hot_reason',
    'northbound': '/user/hadoop/stock_data/signals/northbound',
    'industry_compare': '/user/hadoop/stock_data/signals/industry',
    'dragon_tiger': '/user/hadoop/stock_data/signals/dragon_tiger',
    'fund_flow': '/user/hadoop/stock_data/signals/fund_flow',
    'lockup': '/user/hadoop/stock_data/signals/lockup',
    'concept_blocks': '/user/hadoop/stock_data/signals/concept',
    'fund_nav': '/user/hadoop/stock_data/fund/nav',
    'fund_basic': '/user/hadoop/stock_data/fund/basic',
    'fund_details': '/user/hadoop/stock_data/fund/details',
    'cls_news': '/user/hadoop/stock_data/info/cls_news',
    'global_news': '/user/hadoop/stock_data/info/global_news',
    'research_reports': '/user/hadoop/stock_data/info/research',
    'consensus_eps': '/user/hadoop/stock_data/info/consensus',
    'money_market': '/user/hadoop/stock_data/fund/money_market',
    'etf_market': '/user/hadoop/stock_data/fund/etf',
}

class WebHDFSUploader:
    def __init__(self):
        self.base = HDFS_CFG.get('url', 'http://namenode:9870').rstrip('/')
        self.user = HDFS_CFG.get('user', 'hadoop')

    def _put(self, url, data=None, method='PUT'):
        """带重试的 HTTP PUT"""
        headers = {'Content-Type': 'application/octet-stream'}
        for attempt in range(3):
            try:
                req = Request(url, data=data, headers=headers, method=method)
                resp = urlopen(req, timeout=120)
                return resp
            except HTTPError as e:
                if e.code == 307:
                    # Follow redirect (WebHDFS redirects to DN)
                    loc = e.headers.get('Location', '')
                    if loc:
                        req2 = Request(loc, data=data, headers=headers, method='PUT')
                        return urlopen(req2, timeout=120)
                raise
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def upload(self, local_path, hdfs_path):
        """上传单个文件"""
        if not os.path.isfile(local_path):
            return False
        # Ensure dir exists
        dir_url = f'{self.base}/webhdfs/v1{hdfs_path}?op=MKDIRS&user.name={self.user}'
        self._put(dir_url)

        file_size = os.path.getsize(local_path)
        put_url = f'{self.base}/webhdfs/v1{hdfs_path}/{os.path.basename(local_path)}?op=CREATE&overwrite=true&user.name={self.user}'
        with open(local_path, 'rb') as f:
            self._put(put_url, data=f.read())
        return True

    def upload_all(self, target_dir=None):
        """上传目录下所有 CSV/JSON 文件"""
        src = Path(target_dir or DATA_DIR)
        total = 0
        for f in sorted(src.iterdir()):
            if not f.is_file() or f.suffix.lower() not in ('.csv', '.json'):
                continue
            name = f.name
            hdfs_dir = None
            for prefix, hpath in ROUTES.items():
                if name.startswith(prefix):
                    hdfs_dir = hpath
                    break
            if not hdfs_dir:
                # Default: signals or daily based on content
                hdfs_dir = '/user/hadoop/stock_data/other'
            try:
                self.upload(str(f), hdfs_dir)
                total += 1
                print(f'  ✓ {name} → {hdfs_dir}')
            except Exception as e:
                print(f'  ✗ {name}: {e}')
        print(f'\n📤 上传完成: {total} 个文件')
        return total

    def run_hive_msck(self):
        """执行 MSCK REPAIR TABLE 刷新 Hive 分区"""
        print('  执行 Hive MSCK REPAIR...')
        import subprocess
        try:
            r = subprocess.run(
                ['docker', 'exec', 'hive-server', '/opt/hive/bin/beeline',
                 '-u', 'jdbc:hive2://localhost:10000',
                 '-e', 'MSCK REPAIR TABLE stock_daily;'],
                capture_output=True, text=True, timeout=60)
            print(f'  MSCK: {r.stdout[-200:]}' if r.returncode == 0 else f'  MSCK 跳过: {r.stderr[:200]}')
        except Exception as e:
            print(f'  MSCK 跳过: {e}')

def main():
    import argparse
    parser = argparse.ArgumentParser(description='📤 上传 CSV 到 HDFS（WebHDFS）')
    parser.add_argument('--dir', help='指定目录（默认 /data/raw）')
    parser.add_argument('--file', help='上传单个文件')
    parser.add_argument('--repair', action='store_true', help='上传后执行 MSCK REPAIR')
    args = parser.parse_args()

    uploader = WebHDFSUploader()

    if args.file:
        name = os.path.basename(args.file)
        hdfs_dir = '/user/hadoop/stock_data/uploaded'
        for prefix, hpath in ROUTES.items():
            if name.startswith(prefix):
                hdfs_dir = hpath
                break
        if uploader.upload(args.file, hdfs_dir):
            print(f'✅ {name} → {hdfs_dir}')
        return

    uploaded = uploader.upload_all(args.dir)
    if args.repair and uploaded > 0:
        uploader.run_hive_msck()

if __name__ == '__main__':
    main()
