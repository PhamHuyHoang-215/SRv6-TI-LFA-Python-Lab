
import re
import time
import subprocess
from pathlib import Path

from test_failover_bidirectional import (
    ROOT, R1, R4, H1, DEST, PRIORITY,
    run, router, rules, restore
)

INTERVAL = 0.05
COUNT = 100

def main():
    backup = router(
        R1, "ip", "-6", "route",
        "show", "table", "100"
    ).stdout

    if "2001:db8:200:5::1" not in backup:
        raise RuntimeError("Backup route missing")

    if PRIORITY + ":" in rules():
        raise RuntimeError("Backup rule already active")

    probe = None
    started = False

    try:
        print("=== PREPARE RETURN PATH ===")
        started = True
        router(
            R4, "ip", "-6", "route", "replace",
            "2001:db8:101::/64",
            "via", "2001:db8:45::5", "dev", "eth2"
        )

        run(
            "docker", "cp",
            str(ROOT / "python" / "auto_failover.py"),
            R1 + ":/tmp/auto_failover.py"
        )

        router(
            R1, "sh", "-c",
            "rm -f /tmp/srv6_failover.log"
        )

        run(
            "docker", "exec", "-d", R1,
            "sh", "-c",
            "python3 -u /tmp/auto_failover.py agent "
            "> /tmp/srv6_failover.log 2>&1"
        )

        for _ in range(50):
            pid = router(
                R1, "sh", "-c",
                "cat /tmp/srv6_failover.pid 2>/dev/null || true",
                check=False
            ).stdout.strip()

            if pid.isdigit():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Agent failed to start")

        print("=== START CONTINUOUS PING ===")

        probe = subprocess.Popen(
            [
                "docker", "exec", H1,
                "ping", "-6", "-n", "-D",
                "-i", str(INTERVAL),
                "-c", str(COUNT),
                "-W", "1", DEST
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Gui goi truoc khi gay su co
        time.sleep(1)

        print("=== LINK FAILURE ===")
        failure_time = time.time()

        router(
            R1, "ip", "link", "set",
            "eth1", "down"
        )

        activated = False

        for _ in range(50):
            if PRIORITY + ":" in rules():
                activated = True
                break
            time.sleep(0.05)

        print("Backup activated:", activated)

        output, _ = probe.communicate(timeout=15)

        results = []

        for line in output.splitlines():
            match = re.search(
                r"^\[(\d+(?:\.\d+)?)\]\s+"
                r"\d+ bytes from .*icmp_seq=(\d+)",
                line
            )

            if match:
                results.append((
                    float(match.group(1)),
                    int(match.group(2))
                ))

        received = len(set(seq for _, seq in results))
        lost = COUNT - received
        loss_percent = 100 * lost / COUNT

        gaps = [
            (results[i][0] - results[i-1][0]) * 1000
            for i in range(1, len(results))
        ]

        max_gap = max(gaps, default=0)

        print("\n=== MEASUREMENT RESULTS ===")
        print("Sent:", COUNT)
        print("Received:", received)
        print("Lost:", lost)
        print(f"Packet loss: {loss_percent:.2f}%")
        print(f"Maximum reply gap: {max_gap:.2f} ms")
        print("Failure timestamp:", failure_time)
        print("Backup active:", activated)

        # Luu ket qua de lam bao cao
        output_dir = ROOT / "results"
        output_dir.mkdir(exist_ok=True)

        (output_dir / "failover_ping.txt").write_text(
            output
        )

        print("Saved: results/failover_ping.txt")

        print("\n=== AGENT LOG ===")
        print(router(
            R1, "cat", "/tmp/srv6_failover.log",
            check=False
        ).stdout)

    finally:
        if probe is not None and probe.poll() is None:
            probe.kill()
            probe.communicate()

        if started:
            restore()


if __name__ == "__main__":
    main()
