"""从 SKILL.md 提取关键采集函数的 Python 代码"""
import re, json

with open('SKILL.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有 Python 代码块
blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
print(f'共 {len(blocks)} 个 Python 代码块')

# 关注的关键函数名
targets = [
    'ths_hot_reason', 'dragon_tiger_board', 'daily_dragon_tiger',
    'eastmoney_fund_flow_minute', 'stock_fund_flow_120d',
    'lockup_expiry', 'ths_eps_forecast',
    'eastmoney_stock_news', 'industry_comparison',
    'baidu_kline_with_ma',
]

# 提取所有函数签名所在行
lines = content.split('\n')
func_lines = {}
for i, line in enumerate(lines):
    for t in targets:
        if f'def {t}(' in line:
            func_lines[t] = i
            print(f'  {t}: 行 {i+1}')

# 提取每个函数的完整代码
output = []
for name, start in sorted(func_lines.items(), key=lambda x: x[1]):
    # 从 def 行开始，找到下一个 def 或文件末尾
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith('def ') and j > start + 1:
            end = j
            break
    code = '\n'.join(lines[start:end])
    output.append(f'\n# ====== {name} ======\n{code}')

with open('astock_functions.py', 'w', encoding='utf-8') as f:
    f.write('"""A股数据采集函数 (从 SKILL.md 提取)"""\n')
    f.write('import requests, json, time, re, csv\nfrom datetime import datetime\n\n')
    f.write(''.join(output))

print(f'\n提取完成，共 {len(output)} 个函数')
