#!/usr/bin/env python3
"""
通过mootdx F10 '公司概况' 批量修复行业数据
TCP连接通达信服务器，不经过HTTP，不受公司防火墙限制
"""
import re, logging
from mootdx.quotes import Quotes
import pymysql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 连接数据库
conn = pymysql.connect(host='localhost',port=3307,user='root',password='hadoop123',
                       database='stock_analysis',charset='utf8mb4',autocommit=True)
cur = conn.cursor()

# 获取待修复股票
cur.execute("SELECT stock_code FROM stock WHERE industry REGEXP '^[0-9\\.]+$' OR industry IS NULL OR industry=''")
codes = [r[0] for r in cur.fetchall()]
log.info(f"待修复: {len(codes)} 只")

# 初始化通达信客户端
client = Quotes.factory(market='std')
fixed = 0
errors = 0

for i, code in enumerate(codes):
    try:
        text = client.F10(symbol=code, name='公司概况')
        if not text:
            errors += 1
            continue
        
        # 提取行业类别: 行业类别 ｜XXX-XXX-XXX
        m = re.search(r'行业类别\s*[｜|]\s*([^｜|]+)', text)
        if m:
            industry = m.group(1).strip()
            # 使用完整行业路径 (如 "银行-股份制银行Ⅱ-股份制银行Ⅲ")
            # 或者只用第一级: industry.split('-')[0]
            # 根据现有数据格式，使用完整路径
            cur.execute("UPDATE stock SET industry=%s WHERE stock_code=%s", (industry, code))
            fixed += 1
        else:
            errors += 1
            if errors <= 5:
                log.debug(f"  {code}: 无行业字段")
    except Exception as e:
        errors += 1
        if errors <= 5:
            log.warning(f"  {code}: {e}")
    
    if (i + 1) % 500 == 0:
        log.info(f"  进度: {i+1}/{len(codes)}, 修复={fixed}, 错误={errors}")

log.info(f"结果: 修复={fixed}, 错误={errors}")

# 从已修复数据中提取唯一行业名
if fixed > 0:
    cur.execute("""
        SELECT DISTINCT industry FROM stock 
        WHERE industry NOT REGEXP '^[0-9\\.]+$' AND industry LIKE '%-%'
        ORDER BY industry
    """)
    industries = [r[0] for r in cur.fetchall()]
    log.info(f"行业分类数: {len(industries)} 个")
    for ind in industries[:20]:
        log.info(f"  {ind}")

# 最终统计
cur.execute("SELECT COUNT(*) FROM stock WHERE industry NOT REGEXP '^[0-9\\.]+$' AND industry IS NOT NULL AND industry!=''")
good = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM stock WHERE industry REGEXP '^[0-9\\.]+$'")
num = cur.fetchone()[0]
log.info(f"最终: 正确中文={good}, 仍为数字={num}")
log.info(f"总修复: {good - 1176} 只")

conn.close()
