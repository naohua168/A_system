"""
部署采集的新数据到 HDFS → Hive → Pipeline
将 collect_full_market.py 生成的新CSV上传并建表
"""
import sys, os, glob, time
sys.path.insert(0, '/app/pylib')
import requests
from pyhive import hive

CSV_DIR = '/data/raw'
HDFS_BASE = '/user/hadoop/stock_data'

# CSV前缀 → HDFS目录 → Hive表名 → Hive列定义
SCHEMAS = {
    'tencent_quote': {
        'hdfs': '/user/hadoop/stock_data/tencent_quote',
        'table': 'tencent_quote',
        'columns': 'stock_code STRING, stock_name STRING, price DOUBLE, pe_ttm DOUBLE, pb DOUBLE, mcap_yi DOUBLE, turnover_pct DOUBLE, change_pct DOUBLE',
    },
    'fund_flow': {
        'hdfs': '/user/hadoop/stock_data/fund_flow',
        'table': 'stock_fund_flow',
        'columns': 'stock_code STRING, trade_date STRING, main_net STRING, small_net STRING, mid_net STRING, large_net STRING, super_net STRING',
    },
    'dragon_tiger': {
        'hdfs': '/user/hadoop/stock_data/dragon_tiger',
        'table': 'dragon_tiger',
        'columns': 'trade_date STRING, stock_code STRING, stock_name STRING, reason STRING, net_buy_wan DOUBLE, buy_wan DOUBLE, sell_wan DOUBLE, change_pct DOUBLE',
    },
    'industry_compare': {
        'hdfs': '/user/hadoop/stock_data/industry_compare',
        'table': 'industry_compare',
        'columns': 'industry STRING, code STRING, change_pct DOUBLE, up_count INT, down_count INT',
    },
    'lockup': {
        'hdfs': '/user/hadoop/stock_data/lockup',
        'table': 'stock_lockup',
        'columns': 'stock_code STRING, free_date STRING, lockup_type STRING, shares BIGINT, ratio DOUBLE',
    },
    'stock_news': {
        'hdfs': '/user/hadoop/stock_data/stock_news',
        'table': 'stock_news',
        'columns': 'stock_code STRING, title STRING, content STRING, publish_time STRING, source STRING',
    },
    'concept_blocks': {
        'hdfs': '/user/hadoop/stock_data/concept_blocks',
        'table': 'concept_blocks',
        'columns': 'stock_code STRING, block_name STRING, block_type STRING, change_pct STRING',
    },
    'filings': {
        'hdfs': '/user/hadoop/stock_data/filings',
        'table': 'stock_filings',
        'columns': 'stock_code STRING, title STRING, type STRING, publish_date STRING',
    },
    'tencent_index': {
        'hdfs': '/user/hadoop/stock_data/index/quote',
        'table': 'tencent_index',
        'columns': 'index_code STRING, index_name STRING, price DOUBLE, change_pct DOUBLE, open DOUBLE, high DOUBLE, low DOUBLE, volume BIGINT, amount DOUBLE',
    },
    'index_daily': {
        'hdfs': '/user/hadoop/stock_data/index/daily',
        'table': 'index_daily',
        'columns': 'index_code STRING, trade_date STRING, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, amount DOUBLE, change_pct DOUBLE',
    },
    'stock_industry': {
        'hdfs': '/user/hadoop/stock_data/industry',
        'table': 'stock_industry',
        'columns': 'stock_code STRING, industry STRING, industry_en STRING',
    },
}

def webhdfs_put(local_path, hdfs_path):
    """通过 WebHDFS 上传单个文件"""
    with open(local_path, 'rb') as f:
        data = f.read()
    # 创建目录
    dir_url = f'http://namenode:9870/webhdfs/v1{hdfs_path}?op=MKDIRS&user.name=hadoop'
    try:
        requests.put(dir_url, timeout=10)
    except: pass
    # 上传文件
    fname = os.path.basename(local_path)
    url = f'http://namenode:9870/webhdfs/v1{hdfs_path}/{fname}?op=CREATE&overwrite=true&user.name=hadoop'
    r = requests.put(url, allow_redirects=False, timeout=10)
    if r.status_code == 307:
        loc = r.headers.get('Location', '')
        if loc:
            r2 = requests.put(loc, data=data, timeout=120)
            return r2.status_code in (201, 200)
    return False

def create_hive_table(cursor, name, hdfs_path, columns):
    ddl = f"""
    CREATE EXTERNAL TABLE IF NOT EXISTS {name} (
        {columns}
    )
    ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
    STORED AS TEXTFILE
    LOCATION '{hdfs_path}'
    TBLPROPERTIES ('skip.header.line.count' = '1')
    """
    try:
        cursor.execute(ddl)
        return True
    except Exception as e:
        print(f'  Hive 表 {name} 创建失败: {e}')
        return False

def main():
    print(f'=== 部署新数据到数据链路 ===\n')

    # 1. 上传CSV到HDFS
    print('上传 CSV 到 HDFS...')
    uploaded = {}
    for prefix, schema in SCHEMAS.items():
        files = sorted(glob.glob(os.path.join(CSV_DIR, f'{prefix}_2*.csv')))
        if not files:
            print(f'  {prefix}: 无CSV文件')
            continue
        # 取最新的文件
        latest = files[-1]
        ok = webhdfs_put(latest, schema['hdfs'])
        if ok:
            uploaded[prefix] = schema['hdfs']
            print(f'  {prefix}: {os.path.basename(latest)} ({os.path.getsize(latest)} bytes)')
        time.sleep(0.5)

    if not uploaded:
        print('  无文件可上传')
        return

    # 2. 创建Hive表
    print('\n创建 Hive 外表...')
    conn = hive.connect(host='hive-server', port=10000)
    c = conn.cursor()

    for prefix, schema in SCHEMAS.items():
        if prefix in uploaded:
            create_hive_table(c, schema['table'], schema['hdfs'], schema['columns'])

    # 3. 验证
    print('\n验证 Hive 表数据量...')
    for prefix, schema in SCHEMAS.items():
        if prefix in uploaded:
            try:
                c.execute(f'SELECT COUNT(*) FROM {schema["table"]}')
                cnt = c.fetchone()[0]
                print(f'  {schema["table"]}: {cnt} rows')
            except: pass

    conn.close()
    print(f'\n完成! 上传 {len(uploaded)} 类数据到 HDFS')

if __name__ == '__main__':
    main()
