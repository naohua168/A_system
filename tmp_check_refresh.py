import subprocess, json

# 1. Check how hot_reason is refreshed in auto_seed
r = subprocess.run(['docker','exec','data-collector','sh','-c','grep -n "hot_reason\|hot-reason\|SignalHotReason\|seed_hot\|_ensure_hot\|hot.reason\|HotReason" /app/auto_seed.py | head -20'],
    capture_output=True, timeout=10, text=True)
print("=== auto_seed hot_reason references ===")
print(r.stdout[:1500])

# 2. Check signal data controller for hot_reason source
r2 = subprocess.run(['docker','exec','backend','curl','-s','http://localhost:8082/api/v2/signal/hot-reason?date=2026-06-03'],
    capture_output=True, timeout=10, text=True)
if r2.stdout:
    d = json.loads(r2.stdout)
    arr = d.get('data', [])
    print(f"\n=== hot_reason API: {len(arr)} records ===")
    print(f"First: {json.dumps(arr[0], ensure_ascii=False)}" if arr else "Empty")

# 3. Check if stock_basic has TTL
r3 = subprocess.run(['docker','exec','redis','redis-cli','TTL','market:stock_basic'],
    capture_output=True, timeout=10, text=True)
print(f"\n=== stock_basic TTL: {r3.stdout.strip()}")

# 4. Check if hot_reason controller reads from Redis or DB
r4 = subprocess.run(['docker','exec','redis','redis-cli','EXISTS','market:hot_reason'],
    capture_output=True, timeout=10, text=True)
print(f"=== Redis has market:hot_reason: {r4.stdout.strip()}")
