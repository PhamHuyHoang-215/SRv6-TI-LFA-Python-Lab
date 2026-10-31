
import csv
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "normal_control"
OUT.mkdir(parents=True, exist_ok=True)

RUNS = 10
COUNT = 100
rows = []

for run in range(1, RUNS + 1):
    command = [
        "docker", "exec", "clab-srv6-tilfa5-h1",
        "ping", "-6", "-n", "-D",
        "-i", "0.05", "-c", str(COUNT),
        "-W", "1", "2001:db8:104::10"
    ]

    result = subprocess.run(
        command, capture_output=True, text=True
    )

    (OUT / f"run_{run:02d}.txt").write_text(
        result.stdout + result.stderr
    )

    matches = re.findall(
        r"^\[(\d+(?:\.\d+)?)\]\s+\d+ bytes from "
        r".*icmp_seq=(\d+)",
        result.stdout,
        re.MULTILINE
    )

    times = [float(t) for t, _ in matches]
    received = len(set(int(seq) for _, seq in matches))
    lost = COUNT - received

    gaps = [
        (b - a) * 1000
        for a, b in zip(times, times[1:])
    ]

    max_gap = max(gaps) if gaps else 0

    rows.append({
        "run": run,
        "sent": COUNT,
        "received": received,
        "lost": lost,
        "loss_percent": 100 * lost / COUNT,
        "max_reply_gap_ms": round(max_gap, 2)
    })

    print(
        f"Run {run}/{RUNS}: "
        f"Loss={lost}% | Gap={max_gap:.2f} ms",
        flush=True
    )

with open(OUT / "summary.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("\n=== NORMAL NETWORK SUMMARY ===")
print("Average loss:",
      f"{statistics.mean(r['loss_percent'] for r in rows):.2f}%")
print("Average max reply gap:",
      f"{statistics.mean(r['max_reply_gap_ms'] for r in rows):.2f} ms")
print("CSV:", OUT / "summary.csv")
