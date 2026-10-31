
import sys
import time
import signal
import subprocess
import os
from pathlib import Path

ROUTER = "clab-srv6-tilfa5-r1"
HOST = "clab-srv6-tilfa5-h1"
DEST = "2001:db8:104::10"
PID_FILE = "/tmp/srv6_failover.pid"
PRIORITY = "10100"


def run(command, check=True):
    result = subprocess.run(
        command, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def router(*args, check=True):
    return run(["docker", "exec", ROUTER, *args], check=check)


def rule_exists():
    rules = run(["ip", "-6", "rule", "show"])
    return any(
        line.strip().startswith(PRIORITY + ":")
        for line in rules.splitlines()
    )


# Agent chay truc tiep ben trong Router R1
def agent():
    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    Path(PID_FILE).write_text(str(os.getpid()))

    rule = [
        "ip", "-6", "rule", "add",
        "pref", PRIORITY,
        "from", "2001:db8:101::10/128",
        "to", "2001:db8:104::10/128",
        "iif", "eth3",
        "table", "100"
    ]

    print("Agent monitoring R1 eth1", flush=True)

    try:
        while running:
            state = Path(
                "/sys/class/net/eth1/operstate"
            ).read_text().strip()

            active = rule_exists()

            if state != "up" and not active:
                detected_ns = time.monotonic_ns()

                run(rule)

                activated_ns = time.monotonic_ns()

                print("FAILURE: BACKUP ACTIVE", flush=True)
                print(f"DETECTED_NS={detected_ns}", flush=True)
                print(f"ACTIVATED_NS={activated_ns}", flush=True)
                print(
                    f"RULE_INSTALL_MS="
                    f"{(activated_ns - detected_ns) / 1_000_000:.3f}",
                    flush=True
                )

            elif state == "up" and active:
                run(["ip", "-6", "rule", "del",
                     "pref", PRIORITY])
                print("RECOVERED: PRIMARY ACTIVE", flush=True)

            time.sleep(0.1)
    finally:
        if rule_exists():
            run(["ip", "-6", "rule", "del",
                 "pref", PRIORITY], check=False)

        Path(PID_FILE).unlink(missing_ok=True)


# Chuong trinh dieu khien thu nghiem
def test():
    backup = router("ip", "-6", "route",
                    "show", "table", "100")

    if "2001:db8:200:5::1" not in backup:
        raise RuntimeError("Backup table 100 not installed")

    if PRIORITY + ":" in router("ip", "-6", "rule", "show"):
        raise RuntimeError("Rule 10100 already exists")

    source = Path(__file__).resolve()

    run(["docker", "cp", str(source),
         ROUTER + ":/tmp/auto_failover.py"])

    print("=== START LOCAL AGENT ===")

    try:
        run([
            "docker", "exec", "-d", ROUTER,
            "sh", "-c",
            "python3 -u /tmp/auto_failover.py agent "
            "> /tmp/srv6_failover.log 2>&1"
        ])

        for _ in range(30):
            if router("cat", PID_FILE, check=False):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Agent failed to start")

        print("=== SIMULATE R1-R2 LINK FAILURE ===")
        router("ip", "link", "set", "eth1", "down")

        for _ in range(50):
            if PRIORITY + ":" in router(
                "ip", "-6", "rule", "show"
            ):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Backup activation timeout")

        print("=== ACTIVE ROUTE ===")
        print(router(
            "ip", "-6", "route", "get", DEST,
            "from", "2001:db8:101::10", "iif", "eth3"
        ))

        print("=== PING DURING FAILURE ===")
        result = subprocess.run([
            "docker", "exec", HOST,
            "ping", "-6", "-c", "5", "-W", "1", DEST
        ], capture_output=True, text=True)

        print(result.stdout)

        if result.returncode != 0:
            print("WARNING: Some or all probes failed")

        print("=== AGENT LOG ===")
        print(router(
            "cat", "/tmp/srv6_failover.log",
            check=False
        ))

    finally:
        print("=== RESTORE NETWORK ===")

        router("ip", "link", "set",
               "eth1", "up", check=False)

        time.sleep(0.5)

        pid = router("cat", PID_FILE, check=False)

        if pid.isdigit():
            router("kill", "-TERM", pid, check=False)

        time.sleep(0.3)

        router("ip", "-6", "rule", "del",
               "pref", PRIORITY, check=False)

        router(
            "ip", "-6", "route", "replace",
            "2001:db8:200:2::1/128",
            "via", "2001:db8:12::2", "dev", "eth1"
        )

        router(
            "ip", "-6", "route", "replace",
            "2001:db8:104::/64",
            "encap", "seg6", "mode", "encap",
            "segs",
            "2001:db8:200:2::1,2001:db8:200:4::1",
            "via", "2001:db8:12::2", "dev", "eth1"
        )

        print("Primary route restored")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: auto_failover.py agent|test")

    if sys.argv[1] == "agent":
        agent()
    elif sys.argv[1] == "test":
        test()
    else:
        sys.exit("Unknown mode")
