"""测试 Hive 查询（减小 MR 内存后的验证）"""
import sys
sys.path.insert(0, '/app/pylib')
from pyhive import hive

conn = hive.connect(host='hive-server', port=10000)
c = conn.cursor()

# 设置小内存模式
c.execute('SET mapreduce.map.memory.mb=512')
c.execute('SET mapreduce.reduce.memory.mb=512')
c.execute('SET yarn.app.mapreduce.am.resource.mb=512')
c.execute('SET mapreduce.map.java.opts=-Xmx384m')
c.execute('SET mapreduce.reduce.java.opts=-Xmx384m')
c.execute('SET hive.exec.mode.local.auto=true')

# 测试查询
c.execute('SELECT COUNT(*) FROM stock_basic')
print(f'stock_basic: {c.fetchone()[0]}')

c.execute('SELECT COUNT(*) FROM info_cls_news')
print(f'cls_news: {c.fetchone()[0]}')

c.execute('SELECT COUNT(*) FROM stock_daily')
print(f'stock_daily: {c.fetchone()[0]}')

conn.close()
print('Hive 全部查询成功!')
