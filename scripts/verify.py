"""验证后端 + Redis + Hive 链路"""
import urllib.request, json

# Step 1: Login to get fresh token
data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request('http://localhost:8082/api/user/login', data=data, headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp.get('data', {}).get('token', '')
print(f'Login: code={resp.get("code")}, token={"OK" if token else "FAIL"}')
if not token:
    print('Login failed, exiting')
    exit(1)

h = {'Authorization': f'Bearer {token}'}

# Step 2: Test market API
req = urllib.request.Request('http://localhost:8082/api/market/list?page=1&size=3', headers=h)
try:
    resp = json.loads(urllib.request.urlopen(req).read())
    print(f'Market list: code={resp.get("code")}, records={len(resp.get("data",{}).get("records",[]))}')
except Exception as e:
    print(f'Market list FAIL: {e}')

# Step 3: Test Redis data
import redis
r = redis.Redis(host='127.0.0.1', port=6379, db=0)
print(f'Redis keys: {r.keys("market:*")}')
