"""测试mootdx通达信数据源"""
import os
os.environ['MOOTDX_HOME'] = '/tmp'
from mootdx.quotes import Quotes
q = Quotes.factory(market='std')
print(f'mootdx quote type: {type(q)}')
d = q.bars(symbol='301591', frequency=9, offset=0, start=0, count=10)
if d is not None:
    print(f'301591: {len(d)} bars, columns: {list(d.columns)}')
    print(d.tail(3))
else:
    print('301591: No data')
d2 = q.bars(symbol='000001', frequency=9, offset=0, start=0, count=10)
if d2 is not None:
    print(f'000001: {len(d2)} bars')
else:
    print('000001: No data')
