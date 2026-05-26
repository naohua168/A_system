#!/usr/bin/env python3
"""
从东方财富天天基金API获取基金净值并同步到数据库
"""
import os, sys, time, logging, json, re

os.environ["no_proxy"] = "*"
os.environ["NO_PROXY"] = "*"

import requests
import pymysql

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

conn = pymysql.connect(host='localhost', port=3307, user='root', password='hadoop123',
                       database='stock_analysis', charset='utf8mb4')
cur = conn.cursor()

# 获取所有基金
cur.execute("SELECT fund_code, fund_name, nav, accumulated_nav FROM fund")
funds = [(r[0], r[1], r[2], r[3]) for r in cur.fetchall()]
log.info(f"共 {len(funds)} 只基金")

# 统计当前净值状况
has_nav = sum(1 for f in funds if f[2] and float(f[2]) > 0)
log.info(f"当前有净值: {has_nav}/{len(funds)}")

sess = requests.Session()
sess.trust_env = False
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

updated_nav = 0
updated_acc_nav = 0
errors = 0

for i, (code, name, current_nav, current_acc) in enumerate(funds):
    try:
        # 使用东方财富基金实时行情API
        # 基金secid格式: fundCode.prefix where prefix depends on market
        # 一般基金: 0.000001, 场内ETF: 1.510050
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        r = sess.get(url, headers={"User-Agent": UA}, timeout=10)
        text = r.text
        
        # 解析jsonp: jsonpgz({...})
        json_str = text[text.index('(')+1:text.rindex(')')]
        data = json.loads(json_str)
        
        gztime = data.get("gztime", "")
        nav_val = data.get("dwjz", "")  # 最新净值
        acc_val = data.get("ljjz", "")  # 累计净值
        name_from_api = data.get("name", "")
        nav_date = data.get("jzrq", "")  # 净值日期
        
        if nav_val and float(nav_val) > 0:
            cur.execute(
                "UPDATE fund SET nav=%s, accumulated_nav=%s, updated_at=NOW() WHERE fund_code=%s",
                (float(nav_val), float(acc_val) if acc_val else None, code)
            )
            if cur.rowcount > 0:
                updated_nav += 1
            
            # 同时插入fund_nav表（如果nav_date有效）
            if nav_date:
                try:
                    cur.execute("""
                        INSERT INTO fund_nav (fund_code, nav_date, nav, accumulated_nav, daily_return)
                        VALUES (%s, %s, %s, %s, COALESCE(
                            (SELECT nav FROM fund WHERE fund_code=%s), 0
                        ))
                        ON DUPLICATE KEY UPDATE nav=%s, accumulated_nav=%s
                    """, (code, nav_date, float(nav_val), float(acc_val) if acc_val else None,
                          code, float(nav_val), float(acc_val) if acc_val else None))
                    updated_acc_nav += 1
                except Exception as e2:
                    # fund_nav表可能没有约束，静默跳过
                    pass
        
        if i % 10 == 0:
            log.info(f"进度: {i+1}/{len(funds)}, 更新净值={updated_nav}, 错误={errors}")
        
        time.sleep(0.1)
        
    except Exception as e:
        errors += 1
        if errors <= 5:
            log.warning(f"{code} {name}: 失败 - {e}")

conn.commit()

# 最终统计
cur.execute("SELECT COUNT(*) FROM fund WHERE nav IS NOT NULL AND nav > 0")
nav_after = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM fund_nav")
nav_records = cur.fetchone()[0]

log.info(f"完成: 更新净值={updated_nav}, nav表记录={nav_records}, 错误={errors}")
log.info(f"最终有净值基金: {nav_after}/{len(funds)}")

conn.close()

if nav_after > has_nav:
    log.info(f"✅ 基金净值修复成功! 新增 {nav_after - has_nav} 只")
else:
    log.warning("⚠️ 基金净值未能增加")
