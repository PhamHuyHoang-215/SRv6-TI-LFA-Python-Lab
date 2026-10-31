
#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

R1="clab-srv6-fw-r1"
H1="clab-srv6-fw-h1"
H2="clab-srv6-fw-h2"
DEST="2001:db8:104::10"

restore() {
    trap - EXIT
    set +e

    echo "=== RESTORE PRIMARY ==="

    docker exec "$R1" ip link set eth1 up
    docker exec "$R1" ip -6 addr replace \
        2001:db8:12::1/64 dev eth1

    sleep 2

    docker exec "$R1" sh -c '
        if [ -f /tmp/srv6_failover.pid ]; then
            pid=$(cat /tmp/srv6_failover.pid)
            case "$(ps -p "$pid" -o args= 2>/dev/null)" in
                *"auto_failover.py agent"*)
                    kill -TERM "$pid" 2>/dev/null || true ;;
            esac
        fi
    '

    docker exec "$R1" ip -6 rule del \
        pref 10100 2>/dev/null || true

    docker exec "$R1" ip -6 route replace \
        2001:db8:200:2::1/128 \
        via 2001:db8:12::2 dev eth1

    docker exec "$R1" ip -6 route replace \
        "$DEST/128" encap seg6 mode encap \
        segs 2001:db8:200:2::1,2001:db8:200:5::6 \
        via 2001:db8:12::2 dev eth1

    echo "=== RECOVERY PING ==="
    docker exec "$H1" ping -6 -c 5 -W 1 "$DEST"
}

# Khong thu neu agent cu hoac rule con ton tai
if docker exec "$R1" ip -6 rule show | grep -q '^10100:'; then
    echo "ERROR: Backup rule already active"
    exit 1
fi

if docker exec "$R1" test -f /tmp/srv6_failover.pid; then
    echo "ERROR: Agent PID file exists; inspect first"
    exit 1
fi

trap restore EXIT

echo "=== START PYTHON AGENT ==="

docker cp python/auto_failover.py \
    "$R1:/tmp/auto_failover.py"

docker exec -d "$R1" sh -c \
    'python3 -u /tmp/auto_failover.py agent > /tmp/srv6_failover.log 2>&1'

sleep 1

echo "=== START UDP SERVER ==="

docker exec -d "$H2" iperf3 -s -6 -1 -p 5212
sleep 2

echo "=== START UDP 30 SECONDS ==="

docker exec "$H1" iperf3 -6 -u \
    -c "$DEST" -p 5212 \
    -b 20M -l 1200 -t 30 -i 1 \
    > results/udp_failover_only.txt 2>&1 &

UDP_PID=$!

sleep 8

echo "=== SIMULATE R1-R2 FAILURE ==="

docker exec "$R1" ip link set eth1 down

echo "=== VERIFY BACKUP ACTIVATION ==="

ACTIVE=0

for i in $(seq 1 60); do
    if docker exec "$R1" ip -6 rule show | \
        grep -q '^10100:'; then
        ACTIVE=1
        break
    fi
    sleep 0.1
done

if [ "$ACTIVE" -ne 1 ]; then
    echo "ERROR: Backup activation failed"
    exit 1
fi

docker exec "$R1" ip -6 route get "$DEST" \
    from 2001:db8:101::10 iif eth3

echo "=== WAIT FOR UDP COMPLETION ==="

wait "$UDP_PID"

echo "=== UDP FAILOVER RESULTS ==="

tail -n 12 results/udp_failover_only.txt

echo "=== AGENT LOG ==="

docker exec "$R1" cat /tmp/srv6_failover.log

echo "=== FAILOVER-ONLY TEST COMPLETED ==="
