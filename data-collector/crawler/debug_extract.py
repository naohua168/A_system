"""调试 JS 提取 - 括号计数法"""
import requests, re, json

def extract_js_var(text, var_name):
    """从 JS 中提取变量值（括号计数法，支持嵌套）"""
    idx = text.find(var_name + '=')
    if idx < 0:
        idx = text.find(var_name + ' =')
    if idx < 0:
        return None
    start = text.index('=', idx) + 1
    while start < len(text) and text[start] in ' \t':
        start += 1
    if start >= len(text):
        return None
    brace = text[start]
    if brace == '[':
        open_b, close_b = '[', ']'
    elif brace == '{':
        open_b, close_b = '{', '}'
    elif brace == '"' or brace == "'":
        # 字符串
        end = start + 1
        while end < len(text):
            if text[end] == '\\':
                end += 2
                continue
            if text[end] == brace:
                end += 1
                break
            end += 1
        return text[start:end]
    else:
        # 数值或简单值
        end = start
        while end < len(text) and text[end] not in ';, \t\r\n':
            end += 1
        return text[start:end].strip()
    
    depth = 0
    end = start
    while end < len(text):
        ch = text[end]
        if ch == '\\':
            end += 2
            continue
        if ch == open_b:
            depth += 1
        elif ch == close_b:
            depth -= 1
            if depth == 0:
                end += 1
                break
        elif ch in '"\'':
            # 跳过硬引号
            q = ch
            end += 1
            while end < len(text) and text[end] != q:
                if text[end] == '\\':
                    end += 1
                end += 1
        end += 1
    
    return text[start:end]


r = requests.get('https://fund.eastmoney.com/pingzhongdata/000001.js',
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
txt = r.text

# Test extraction
raw_mgr = extract_js_var(txt, 'Data_currentFundManager')
print(f'currentFundManager ({len(raw_mgr)} chars)')
if raw_mgr:
    try:
        mgrs = json.loads(raw_mgr)
        for m in mgrs:
            print(f'  Manager: {m.get("name")} | Size: {m.get("fundSize")}')
    except Exception as e:
        print(f'  JSON parse error: {e}')
        print(f'  Raw preview: {raw_mgr[:200]}')

raw_scale = extract_js_var(txt, 'Data_fluctuationScale')
print(f'\nfluctuationScale ({len(raw_scale)} chars)')
if raw_scale:
    try:
        obj = json.loads(raw_scale)
        series = obj.get('series', [])
        if series:
            print(f'  Latest scale: {series[-1].get("y")}')
        print(f'  Categories: {obj.get("categories")}')
    except Exception as e:
        print(f'  JSON parse error: {e}')
