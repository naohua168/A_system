"""检查 fund_crawler.py 的 fetch_fund_detail 是否能正确提取 JS 变量"""
import requests, re

r = requests.get('https://fund.eastmoney.com/pingzhongdata/000001.js',
                 headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
txt = r.text

# 用当前 fund_crawler.py 里的正则测试
patterns = {
    'company': (r'Data_ManagerCompany\s*=\s*["\']([^"\']+)', '字符串'),
    'manager': (r'Data_Manager\s*=\s*["\']([^"\']+)', '字符串'),
    'scale': (r'Data_FundScale\s*=\s*([\d.]+)', '数字'),
    'fund_type': (r'Data_FundType\s*=\s*["\']([^"\']+)', '字符串'),
}

for name, (pat, desc) in patterns.items():
    m = re.search(pat, txt)
    if m:
        val = m.group(1)
        print(f'  {name} = {val}  [{desc}]')
    else:
        print(f'  {name}: ❌ 未匹配')

# 也看看实际有哪些 Data_ 变量
vars_found = sorted(set(re.findall(r'(Data_\w+)\s*=', txt)))
print(f'\n实际 JS 中的 Data_ 变量 ({len(vars_found)}):')
for v in vars_found[:20]:
    print(f'  {v}')
