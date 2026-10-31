
import csv
import re
import shutil
import subprocess
import sys
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "python" / "measure_failover.py"
SOURCE_PING = ROOT / "results" / "failover_ping.txt"

RUNS = 10

# Moi dot thu nghiem co thu muc rieng
batch_name = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
output_dir = ROOT / "results" / batch_name
output_dir.mkdir(parents=True, exist_ok=True)


def extract(pattern, text, cast=float):
    match = re.search(pattern, text)
    return cast(match.group(1)) if match else None


results = []

for i in range(1, RUNS + 1):
    print(f"\n=== TEST {i}/{RUNS} ===", flush=True)

    # Xoa file ping cu de tranh lay nham du lieu
    SOURCE_PING.unlink(missing_ok=True)

    # Chay phep do hien tai
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        log = proc.stdout + "\n" + proc.stderr
        exit_code = proc.returncode

    except subprocess.TimeoutExpired as exc:
        log = str(exc)
        exit_code = -1

    # Luu Terminal output
    (output_dir / f"run_{i:02d}.log").write_text(log)

    # Luu du lieu ping goc
    if SOURCE_PING.exists():
        shutil.copy2(
            SOURCE_PING,
            output_dir / f"run_{i:02d}_ping.txt"
        )

    sent = extract(r"Sent:\s*(\d+)", log, int)
    received = extract(r"Received:\s*(\d+)", log, int)
    lost = extract(r"Lost:\s*(\d+)", log, int)
    loss = extract(r"Packet loss:\s*([\d.]+)%", log)
    gap = extract(r"Maximum reply gap:\s*([\d.]+)", log)

    backup_active = "Backup active: True" in log
    recovered = (
        "=== RECOVERY PING ===" in log
        and "3 packets transmitted, 3 received" in log
    )

    valid = (
        exit_code == 0
        and sent == 100
        and received is not None
        and lost is not None
        and gap is not None
        and backup_active
        and recovered
    )

    row = {
        "run": i,
        "sent": sent,
        "received": received,
        "lost": lost,
        "loss_percent": loss,
        "max_reply_gap_ms": gap,
        "backup_active": backup_active,
        "recovered": recovered,
        "status": "MEASURED" if valid else "CHECK"
    }

    results.append(row)

    print(
        f"Loss={loss}% | Gap={gap} ms | "
        f"Status={row['status']}",
        flush=True
    )

    # Dung neu thu nghiem gap loi
    if not valid:
        print("STOP: Check the run log before retrying.")
        break


# Xuat CSV
csv_file = output_dir / "summary.csv"

with open(csv_file, "w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=results[0].keys()
    )
    writer.writeheader()
    writer.writerows(results)


# Thong ke cac phep do hop le
valid_results = [
    row for row in results
    if row["status"] == "MEASURED"
]

print("\n=== FINAL SUMMARY ===")

if valid_results:
    losses = [r["loss_percent"] for r in valid_results]
    gaps = [r["max_reply_gap_ms"] for r in valid_results]

    print("Valid runs:", len(valid_results))
    print(f"Average loss: {statistics.mean(losses):.2f}%")
    print(f"Average max reply gap: {statistics.mean(gaps):.2f} ms")
    print(f"Worst reply gap: {max(gaps):.2f} ms")

print("CSV:", csv_file)
