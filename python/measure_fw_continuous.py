#!/usr/bin/env python3
"""Continuous ICMPv6 measurement during Python SRv6 Firewall failover (v2).

This is a lab test, not an RFC 9855 TI-LFA convergence measurement.
Run from project root: sudo python3 python/measure_fw_continuous.py --runs 1
"""
import argparse
import csv
import re
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
SRC = "2001:db8:101::10"
DST = "2001:db8:104::10"
PRIORITY = "10100"
COUNT = 100
INTERVAL = "0.05"


def cmd(args, check=True, timeout=10):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {p.stderr or p.stdout}")
    return p.stdout


def node(container, *args, check=True, timeout=10):
    return cmd(["docker", "exec", container, *args], check=check, timeout=timeout)


def rule_active():
    return bool(re.search(r"^10100:", node(R1, "ip", "-6", "rule", "show"), re.M))


def fw_counters():
    output = node(FW, "nft", "list", "chain", "ip6", "srv6_waypoint", "transit")
    counts = []
    for ingress, egress in [("eth1", "eth2"), ("eth2", "eth1")]:
        match = re.search(
            rf'iifname "{ingress}" oifname "{egress}"[^\n]*?counter packets (\d+)',
            output,
        )
        if not match:
            raise RuntimeError(f"Firewall counter missing for {ingress}->{egress}")
        counts.append(int(match.group(1)))
    return counts


def bypass_drops():
    output = node(R5, "nft", "list", "chain", "inet", "bypass_guard", "forward")
    match = re.search(r'oifname "eth2"\s+counter packets (\d+)\s+bytes \d+ drop', output)
    if not match:
        raise RuntimeError("Bypass guard not found")
    return int(match.group(1))


def preflight():
    if rule_active():
        raise RuntimeError("Rule 10100 already active; inspect R1 before retesting")
    pid = node(R1, "sh", "-c", "cat /tmp/srv6_failover.pid 2>/dev/null || true").strip()
    if pid:
        raise RuntimeError(f"Agent PID file exists ({pid}); inspect agent before retesting")
    if "2001:db8:200:5::6" not in node(R1, "ip", "-6", "route", "show", "table", "100"):
        raise RuntimeError("Backup route table 100 missing")
    main = node(R1, "ip", "-6", "route", "get", DST, "from", SRC, "iif", "eth3")
    if "dev eth1" not in main or "2001:db8:200:2::1" not in main:
        raise RuntimeError(f"Primary route not active: {main}")
    ret = node(R4, "ip", "-6", "route", "get", SRC)
    if "via 2001:db8:64::6" not in ret:
        raise RuntimeError("R4 return path is not via Firewall")
    fw_counters()
    bypass_drops()


def restore():
    """Recover R1-R2 underlay before reinstalling SRv6 routes.

    When eth1 goes DOWN, Linux can remove the connected IPv6 route and
    sometimes the global address.  Merely bringing eth1 UP is insufficient.
    """
    print("=== RESTORE PRIMARY (IPv6 ADDRESS + SRv6) ===", flush=True)
    errors = []

    # Stop the local polling agent; otherwise it may race with cleanup.
    try:
        pid = node(R1, "sh", "-c",
                   "cat /tmp/srv6_failover.pid 2>/dev/null || true",
                   check=False).strip()
        if pid.isdigit():
            node(R1, "kill", "-TERM", pid, check=False)
            for _ in range(30):
                alive = node(R1, "sh", "-c",
                             "test -f /tmp/srv6_failover.pid && echo YES || true",
                             check=False).strip()
                if not alive:
                    break
                time.sleep(0.1)
            else:
                errors.append("Agent PID file remained after SIGTERM")
    except Exception as exc:
        errors.append(f"Agent stop: {exc}")

    # Restore the interface AND its IPv6 address; keep these in this order.
    for label, args in [
        ("Bring R1 eth1 up", ["ip", "link", "set", "eth1", "up"]),
        ("Restore R1-R2 IPv6 address",
         ["ip", "-6", "addr", "replace", "2001:db8:12::1/64", "dev", "eth1"]),
    ]:
        try:
            node(R1, *args)
            print(f"OK: {label}", flush=True)
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    # Wait for connected IPv6 routing / DAD readiness.  Never fall back to
    # Containerlab's management eth0 as a substitute for the data-plane link.
    ready = False
    for _ in range(20):
        try:
            connected = node(R1, "ip", "-6", "route", "get", "2001:db8:12::2",
                             "from", "2001:db8:12::1", check=False)
            if "dev eth1" in connected:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.25)
    if not ready:
        errors.append("R1-R2 connected IPv6 route did not return on eth1")

    # Remove only the rule used for this specific experiment.
    try:
        if rule_active():
            node(R1, "ip", "-6", "rule", "del", "pref", PRIORITY)
        print("OK: backup policy rule removed", flush=True)
    except Exception as exc:
        errors.append(f"Remove backup rule: {exc}")

    # Reinstall both routes.  Fail loudly if the next-hop is still unavailable.
    routes = [
        ("R2 SID", ["ip", "-6", "route", "replace", "2001:db8:200:2::1/128",
                     "via", "2001:db8:12::2", "dev", "eth1"]),
        ("Primary SRv6", ["ip", "-6", "route", "replace", f"{DST}/128",
                          "encap", "seg6", "mode", "encap", "segs",
                          "2001:db8:200:2::1,2001:db8:200:5::6",
                          "via", "2001:db8:12::2", "dev", "eth1"]),
    ]
    for label, args in routes:
        restored = False
        last_error = ""
        for _ in range(12):
            try:
                node(R1, *args)
                print(f"OK: {label} restored", flush=True)
                restored = True
                break
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.25)
        if not restored:
            errors.append(f"{label}: {last_error}")

    try:
        primary = node(R1, "ip", "-6", "route", "get", DST,
                       "from", SRC, "iif", "eth3")
        print("Primary route:", primary.strip(), flush=True)
        if "dev eth1" not in primary or "2001:db8:200:2::1" not in primary:
            errors.append("Primary traffic did not return to R1-R2 SRv6 path")
    except Exception as exc:
        errors.append(f"Verify primary route: {exc}")

    print("=== RECOVERY PING ===", flush=True)
    try:
        recovery = node(H1, "ping", "-6", "-c", "3", "-W", "1", DST,
                        check=False, timeout=10)
        print(recovery, flush=True)
        if "3 received" not in recovery:
            errors.append("Recovery ping did not receive all 3 replies")
    except Exception as exc:
        errors.append(f"Recovery ping: {exc}")

    if errors:
        raise RuntimeError("Restore requires inspection: " + "; ".join(errors))
    print("NETWORK RESTORED", flush=True)


def measure(run_number, outdir):
    preflight()
    print(f"\n=== FIREWALL CONTINUOUS TEST {run_number} ===", flush=True)
    baseline = node(H1, "ping", "-6", "-c", "2", "-W", "1", DST, check=False, timeout=8)
    if "2 received" not in baseline:
        raise RuntimeError("Baseline ping failed")

    before_fw = fw_counters()
    before_drop = bypass_drops()
    probe = None
    changed = False
    try:
        changed = True
        cmd(["docker", "cp", str(ROOT / "python" / "auto_failover.py"), f"{R1}:/tmp/auto_failover.py"])
        node(R1, "rm", "-f", "/tmp/srv6_failover.log")
        cmd(["docker", "exec", "-d", R1, "sh", "-c",
             "python3 -u /tmp/auto_failover.py agent > /tmp/srv6_failover.log 2>&1"])
        for _ in range(60):
            pid = node(R1, "sh", "-c", "cat /tmp/srv6_failover.pid 2>/dev/null || true", check=False).strip()
            if pid.isdigit():
                break
            time.sleep(0.1)
        else:
            print(node(R1, "cat", "/tmp/srv6_failover.log", check=False))
            raise RuntimeError("Python agent did not start")

        print("=== START CONTINUOUS PING ===", flush=True)
        probe = subprocess.Popen(
            ["docker", "exec", H1, "ping", "-6", "-n", "-D", "-i", INTERVAL,
             "-c", str(COUNT), "-W", "1", DST],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        time.sleep(1.0)  # around 20 probes before the fault
        if probe.poll() is not None:
            raise RuntimeError("Ping exited before link failure")

        print("=== LINK DOWN WHILE PING IS RUNNING ===", flush=True)
        failure = node(R1, "python3", "-c",
                       "import time,subprocess; t=time.monotonic_ns(); "
                       "subprocess.run(['ip','link','set','eth1','down'],check=True); print(t)")
        failure_ns = int(failure.strip())
        for _ in range(100):
            if rule_active():
                break
            time.sleep(0.02)
        else:
            raise RuntimeError("Backup did not activate")

        raw, _ = probe.communicate(timeout=15)
        (outdir / f"run_{run_number:02d}_ping.txt").write_text(raw)
        log = node(R1, "cat", "/tmp/srv6_failover.log")
        (outdir / f"run_{run_number:02d}_agent.log").write_text(log)
        print("=== AGENT LOG ===\n" + log, flush=True)

        hits = re.findall(r'^\[(\d+(?:\.\d+)?)\]\s+\d+ bytes from .*icmp_seq=(\d+)', raw, re.M)
        seqs = {int(seq) for _, seq in hits}
        times = [float(ts) for ts, _ in hits]
        lost = COUNT - len(seqs)
        missing = sorted(set(range(1, COUNT + 1)) - seqs)
        max_gap = max(((b - a) * 1000 for a, b in zip(times, times[1:])), default=0.0)
        after_fw = fw_counters()
        after_drop = bypass_drops()
        forward = after_fw[0] - before_fw[0]
        reverse = after_fw[1] - before_fw[1]
        drops = after_drop - before_drop
        det = re.search(r"DETECTED_NS=(\d+)", log)
        act = re.search(r"ACTIVATED_NS=(\d+)", log)
        detect_ms = (int(det.group(1)) - failure_ns) / 1e6 if det else None
        activate_ms = (int(act.group(1)) - failure_ns) / 1e6 if act else None
        row = dict(run=run_number, sent=COUNT, received=len(seqs), lost=lost,
                   loss_percent=round(lost * 100 / COUNT, 2),
                   max_reply_gap_ms=round(max_gap, 3),
                   detection_interval_ms=round(detect_ms, 3) if detect_ms is not None else "",
                   activation_interval_ms=round(activate_ms, 3) if activate_ms is not None else "",
                   fw_forward_delta=forward, fw_reverse_delta=reverse,
                   bypass_drop_delta=drops)
        print("=== MEASUREMENT RESULTS ===", flush=True)
        for key, value in row.items():
            print(f"{key}: {value}", flush=True)
        print("Missing sequences:", missing, flush=True)
        if forward < len(seqs) or reverse < len(seqs) or drops != 0:
            raise RuntimeError("Firewall counter or bypass-guard verification failed")
        return row
    finally:
        if probe is not None and probe.poll() is None:
            probe.kill()
            probe.communicate()
        if changed:
            restore()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.runs <= 20:
        parser.error("--runs must be between 1 and 20")
    outdir = ROOT / "results" / ("fw_continuous_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index in range(1, args.runs + 1):
        try:
            row = measure(index, outdir)
            rows.append(row)
        except Exception as exc:
            print(f"STOP after run {index}: {exc}", flush=True)
            break
        finally:
            if rows:
                with (outdir / "summary.csv").open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
    print(f"\nCompleted: {len(rows)}/{args.runs}", flush=True)
    print("Results:", outdir, flush=True)
    if len(rows) != args.runs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
