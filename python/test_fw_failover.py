#!/usr/bin/env python3
"""SRv6 firewall-waypoint failover lab verification (NOT RFC 9855 TI-LFA).

Run on Ubuntu host in ~/srv6-tilfa-python-starter:
    sudo python3 python/test_fw_failover_v2.py --runs 1
    sudo python3 python/test_fw_failover_v2.py --runs 10

Requires existing srv6-fw topology, table 100, nftables firewall and
python/auto_failover.py agent with DETECTED_NS and ACTIVATED_NS logging.
"""

import argparse
import csv
import re
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R1 = "clab-srv6-fw-r1"
R4 = "clab-srv6-fw-r4"
R5 = "clab-srv6-fw-r5"
FW = "clab-srv6-fw-fw"
H1 = "clab-srv6-fw-h1"
DEST = "2001:db8:104::10"
SOURCE = "2001:db8:101::10"
PRIORITY = "10100"
AGENT = ROOT / "python" / "auto_failover.py"


def run(*args, check=True, timeout=15):
    proc = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout
    )
    if check and proc.returncode:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(args)}\n"
            f"{proc.stderr or proc.stdout}"
        )
    return proc


def node(container, *args, check=True, timeout=15):
    return run("docker", "exec", container, *args, check=check, timeout=timeout)


def rule_active():
    output = node(R1, "ip", "-6", "rule", "show").stdout
    return bool(re.search(r"^\s*10100:", output, flags=re.MULTILINE))


def agent_pid():
    output = node(
        R1, "sh", "-c",
        "cat /tmp/srv6_failover.pid 2>/dev/null || true",
        check=False,
    ).stdout.strip()
    return output if output.isdigit() else None


def agent_is_running(pid):
    if not pid:
        return False
    p = node(R1, "ps", "-p", pid, "-o", "args=", check=False)
    return "auto_failover.py agent" in p.stdout


def ping(count):
    p = node(
        H1, "ping", "-6", "-c", str(count), "-W", "1", DEST,
        check=False, timeout=max(10, count + 8)
    )
    print(p.stdout, flush=True)
    if p.returncode != 0 or f"{count} received" not in p.stdout:
        raise RuntimeError(f"Ping failed: {p.stderr or p.stdout}")


def firewall_counters():
    out = node(
        FW, "nft", "list", "chain", "ip6", "srv6_waypoint", "transit"
    ).stdout
    forward = reverse = None
    for line in out.splitlines():
        match = re.search(r"counter packets (\d+)", line)
        if not match:
            continue
        if 'iifname "eth1" oifname "eth2"' in line:
            forward = int(match.group(1))
        elif 'iifname "eth2" oifname "eth1"' in line:
            reverse = int(match.group(1))
    if forward is None or reverse is None:
        raise RuntimeError("Missing firewall counter rules")
    return (forward, reverse)


def bypass_drops():
    out = node(
        R5, "nft", "list", "chain", "inet", "bypass_guard", "forward"
    ).stdout
    match = re.search(
        r'oifname "eth2"\s+counter packets (\d+)\s+bytes \d+ drop', out
    )
    if not match:
        raise RuntimeError("Bypass guard is not installed")
    return int(match.group(1))


def restore():
    """Undo only the changes caused by this test. Never rerun full setup scripts."""
    print("\n=== RESTORE NETWORK (DIRECT, WITH TIMEOUTS) ===", flush=True)
    errors = []

    def attempt(description, *cmd, retries=1):
        last = None
        for _ in range(retries):
            try:
                result = node(R1, *cmd, check=False, timeout=12)
                if result.returncode == 0:
                    return
                last = (result.stderr or result.stdout).strip()
            except Exception as exc:
                last = str(exc)
            time.sleep(0.3)
        errors.append(f"{description}: {last}")

    # Bring up R1-R2 and stop the Python polling agent.
    attempt("Bring up eth1", "ip", "link", "set", "eth1", "up")
    pid = agent_pid()
    if agent_is_running(pid):
        node(R1, "kill", "-TERM", pid, check=False)
        time.sleep(0.4)
    # The normal agent removes its PID file and policy rule on exit.
    if agent_pid() and not agent_is_running(agent_pid()):
        node(R1, "rm", "-f", "/tmp/srv6_failover.pid", check=False)
    if rule_active():
        attempt("Remove backup rule", "ip", "-6", "rule", "del", "pref", PRIORITY)

    # Linux may withdraw IPv6 connected routes when the interface goes down.
    attempt(
        "Restore R1-R2 IPv6 address", "ip", "-6", "addr", "replace",
        "2001:db8:12::1/64", "dev", "eth1"
    )
    attempt(
        "Restore route to R2 SID", "ip", "-6", "route", "replace",
        "2001:db8:200:2::1/128", "via", "2001:db8:12::2", "dev", "eth1",
        retries=5
    )
    attempt(
        "Restore primary SRv6 steering", "ip", "-6", "route", "replace",
        DEST + "/128", "encap", "seg6", "mode", "encap", "segs",
        "2001:db8:200:2::1,2001:db8:200:5::6",
        "via", "2001:db8:12::2", "dev", "eth1", retries=5
    )

    if errors:
        print("RESTORE WARNINGS:", *errors, sep="\n- ", flush=True)
        raise RuntimeError("Network restoration needs manual inspection")

    if rule_active():
        raise RuntimeError("Backup policy rule is still active")

    route = node(
        R1, "ip", "-6", "route", "get", DEST,
        "from", SOURCE, "iif", "eth3"
    ).stdout
    print("Primary route:", route.strip(), flush=True)
    if "dev eth1" not in route or "2001:db8:200:2::1" not in route:
        raise RuntimeError("Primary route was not restored")
    print("=== RECOVERY PING ===", flush=True)
    ping(3)
    print("NETWORK RESTORED", flush=True)


def preflight():
    if not AGENT.is_file():
        raise RuntimeError(f"Agent file not found: {AGENT}")
    backup = node(R1, "ip", "-6", "route", "show", "table", "100").stdout
    if "2001:db8:200:5::6" not in backup:
        raise RuntimeError("Missing service SID in preinstalled backup table 100")
    if rule_active():
        raise RuntimeError("Rule 10100 is already active; do not overlap tests")
    oldpid = agent_pid()
    if agent_is_running(oldpid):
        raise RuntimeError("An agent is already running; do not overlap tests")
    if oldpid:
        node(R1, "rm", "-f", "/tmp/srv6_failover.pid")
    reply_route = node(R4, "ip", "-6", "route", "get", SOURCE).stdout
    if "via 2001:db8:64::6" not in reply_route:
        raise RuntimeError("Return traffic from R4 does not use the firewall")
    firewall_counters()
    bypass_drops()


def one_run(run_id):
    preflight()
    print(f"\n=== RUN {run_id}: BASELINE PING ===", flush=True)
    ping(3)
    initial_fw = firewall_counters()
    initial_drop = bypass_drops()

    started_agent = False
    try:
        print("=== START PYTHON AGENT ===", flush=True)
        run("docker", "cp", str(AGENT), R1 + ":/tmp/auto_failover.py")
        node(R1, "rm", "-f", "/tmp/srv6_failover.log", check=False)
        run(
            "docker", "exec", "-d", R1, "sh", "-c",
            "python3 -u /tmp/auto_failover.py agent "
            "> /tmp/srv6_failover.log 2>&1",
        )
        started_agent = True
        for _ in range(60):
            if agent_is_running(agent_pid()):
                break
            time.sleep(0.1)
        else:
            log = node(R1, "cat", "/tmp/srv6_failover.log", check=False).stdout
            raise RuntimeError(f"Agent did not start:\n{log}")

        print("=== SIMULATE FAILURE ===", flush=True)
        p = node(
            R1, "python3", "-c",
            "import time,subprocess; t=time.monotonic_ns(); "
            "subprocess.run(['ip','link','set','eth1','down'],check=True); print(t)"
        )
        failure_ns = int(p.stdout.strip())

        print("=== WAIT FOR BACKUP ===", flush=True)
        for _ in range(100):
            if rule_active():
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("Backup activation timeout")

        route = node(
            R1, "ip", "-6", "route", "get", DEST,
            "from", SOURCE, "iif", "eth3"
        ).stdout
        print(route, flush=True)
        if "table 100" not in route or "dev eth2" not in route:
            raise RuntimeError("Backup route is not active")

        print("=== PING DURING FAILURE ===", flush=True)
        ping(5)

        after_fw = firewall_counters()
        after_drop = bypass_drops()
        df = after_fw[0] - initial_fw[0]
        dr = after_fw[1] - initial_fw[1]
        dd = after_drop - initial_drop
        print("=== FIREWALL COUNTERS ===", flush=True)
        print(f"H1->H2: +{df} | H2->H1: +{dr} | Bypass drops: +{dd}", flush=True)
        if df < 5 or dr < 5 or dd != 0:
            raise RuntimeError("Firewall waypoint/bypass checks failed")

        log = node(R1, "cat", "/tmp/srv6_failover.log").stdout
        print("=== AGENT LOG ===\n" + log, flush=True)
        d = re.search(r"DETECTED_NS=(\d+)", log)
        a = re.search(r"ACTIVATED_NS=(\d+)", log)
        if not (d and a):
            raise RuntimeError("Agent log lacks monotonic timestamps")
        detection = (int(d.group(1)) - failure_ns) / 1e6
        activation = (int(a.group(1)) - failure_ns) / 1e6
        installation = (int(a.group(1)) - int(d.group(1))) / 1e6
        if min(detection, activation, installation) < 0:
            raise RuntimeError("Unexpected timestamp ordering")
        print("=== TIMING (NOT END-TO-END SERVICE RECOVERY) ===", flush=True)
        print(
            f"Detection interval: {detection:.3f} ms | "
            f"Activation interval: {activation:.3f} ms | "
            f"Rule install: {installation:.3f} ms",
            flush=True,
        )
        print("FIREWALL FAILOVER: PASS", flush=True)
        return {
            "run": run_id,
            "detection_interval_ms": round(detection, 3),
            "activation_interval_ms": round(activation, 3),
            "rule_install_ms": round(installation, 3),
            "fw_forward_delta": df,
            "fw_reverse_delta": dr,
            "bypass_drop_delta": dd,
            "ping_during_failure": "5/5",
            "status": "PASS",
        }
    finally:
        if started_agent:
            restore()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.runs <= 50:
        parser.error("--runs must be between 1 and 50")

    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    outfile = output_dir / (
        f"fw_failover_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )
    rows = []
    for i in range(1, args.runs + 1):
        try:
            row = one_run(i)
        except Exception as exc:
            print(f"ERROR on run {i}: {exc}", flush=True)
            print("STOP: Inspect network state before another attempt.", flush=True)
            break
        else:
            rows.append(row)

    if rows:
        with outfile.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print("\n=== BATCH SUMMARY ===", flush=True)
        print(f"Successful runs: {len(rows)}/{args.runs}", flush=True)
        for name in (
            "detection_interval_ms", "activation_interval_ms", "rule_install_ms"
        ):
            values = [r[name] for r in rows]
            print(f"Mean {name}: {statistics.mean(values):.3f} ms", flush=True)
        print("CSV:", outfile, flush=True)
    if len(rows) != args.runs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
