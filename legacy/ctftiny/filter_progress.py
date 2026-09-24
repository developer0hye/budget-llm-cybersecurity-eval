import sys, json
n = 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    n += 1
    try:
        row = json.loads(line)
    except Exception:
        continue
    if row.get("solved"):
        print(f"[{n}] SOLVE: {row['model']} / {row['challenge']}", flush=True)
    elif n % 25 == 0:
        print(f"[{n}] progress checkpoint: {row['model']} / {row['challenge']} -> {row.get('finish_reason', row.get('error','?'))[:60]}", flush=True)
