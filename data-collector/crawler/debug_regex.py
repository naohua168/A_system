"""调试 JS 正则匹配"""
import requests, re, json

r = requests.get('https://fund.eastmoney.com/pingzhongdata/000001.js',
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
txt = r.text

# 测试 Data_currentFundManager
m = re.search(r'Data_currentFundManager\s*=\s*(\[[^\]]+\])', txt, re.DOTALL)
print(f'currentFundManager Match: {m}')
if m:
    raw = m.group(1)
    print(f'Raw ({len(raw)} chars): {raw[:300]}')
    try:
        mgrs = json.loads(raw)
        print(f'Parsed OK: manager={mgrs[0].get("name", "")}')
    except Exception as e:
        print(f'JSON parse error: {e}')
else:
    # 看看实际变量的前后文
    idx = txt.find('Data_currentFundManager')
    if idx >= 0:
        print(f'Found at pos {idx}: {txt[idx:idx+100]}')
    else:
        print('Data_currentFundManager NOT FOUND in JS!')
    
# 测试 Data_fluctuationScale
m = re.search(r'Data_fluctuationScale\s*=\s*({[^}]+})', txt, re.DOTALL)
print(f'\nfluctuationScale Match: {m}')
if m:
    raw = m.group(1)
    print(f'Raw ({len(raw)} chars): {raw[:300]}')
    try:
        obj = json.loads(raw)
        series = obj.get("series", [])
        if series:
            print(f'Parsed OK: scale={series[-1].get("y", 0)}')
    except Exception as e:
        print(f'JSON parse error: {e}')
else:
    idx = txt.find('Data_fluctuationScale')
    if idx >= 0:
        print(f'Found at pos {idx}: {txt[idx:idx+100]}')
    else:
        print('Data_fluctuationScale NOT FOUND!')
