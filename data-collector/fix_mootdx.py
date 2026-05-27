import re, os

for path in [
    '/usr/local/lib/python3.11/site-packages/mootdx/utils/__init__.py',
    '/usr/local/lib/python3.11/site-packages/mootdx/config.py'
]:
    with open(path, 'r') as f:
        content = f.read()
    new = content.replace('/nonexistent', '/tmp')
    with open(path, 'w') as f:
        f.write(new)
    print(f'Patched: {path}')
