import redis, json
r = redis.Redis(host='127.0.0.1', port=6379, db=0)
print('dbsize:', r.dbsize())
# 测试写入
r.setex('market:stock_industry', 600, json.dumps({'test': 'ok'}))
print('setex done, reading back...')
v = r.get('market:stock_industry')
print('read back:', v[:30] if v else 'NULL')
r.delete('market:stock_industry')
print('cleaned up')
