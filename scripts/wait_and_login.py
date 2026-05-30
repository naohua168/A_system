"""持续尝试登录直到成功"""
import urllib.request, json, time
for i in range(18):
    try:
        d = json.dumps({'username':'admin','password':'admin123'}).encode()
        req = urllib.request.Request('http://localhost:8082/api/user/login', data=d, headers={'Content-Type':'application/json'})
        r = json.loads(urllib.request.urlopen(req, timeout=5).read())
        code = r.get('code')
        if code == 200:
            token = r.get('data', {}).get('token', '')
            print(f'OK: 登录成功 token={token[:20]}...')
            break
        else:
            print(f'RETRY: code={code} msg={r.get("message")}')
    except Exception as e:
        print(f'RETRY: {type(e).__name__}')
    time.sleep(10)
else:
    print('FAILED: 所有重试均失败')
