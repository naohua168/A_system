#!/usr/bin/env python3
import requests, json

s = requests.Session()
r = s.post('http://backend:8082/api/user/login', json={'username':'admin','password':'admin123'}, timeout=10)
token = r.json().get('data', {}).get('token', '')
s.headers.update({'Authorization': f'Bearer {token}'})

r2 = s.get('http://backend:8082/api/market/etf', params={'page':1,'size':3}, timeout=10)
d = r2.json()
print("API返回:", json.dumps(d.get('data', {}).get('records', [])[0], indent=2, ensure_ascii=False))
