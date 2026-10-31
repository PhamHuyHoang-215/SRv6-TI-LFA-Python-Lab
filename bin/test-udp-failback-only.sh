
#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

R1="clab-srv6-fw-r1"
H1="clab-srv6-fw-h1"
H2="clab-srv6-fw-h2"
DEST="2001:db8:104::10"
PORT=5213

restore() {
    trap - EXIT
    set +e

    echo "=== RESTORE PRIMARY ==="

    docker exec "$R1" ip link set eth1 up
    docker exec "$R1" ip -6 addr replace \
        2001:db8:12::1/64 dev eth1

    sleep 2

    docker exec "$R1" ip -6 route replace \
        2001:db8:200:2::1/128 \
        via 2001:db8:12::2 dev eth1

    docker exec "$R1" ip -6 route replace \
        "$DEST/128" \
        encap seg6 mode encap \
        segs 2001:db8:200:2::1,2001:db8:200:5::6 \
        via 2001:db8:12::2 dev eth1

    docker exec "$R1" ip -6 rule del \
        pref 10100 2>/dev/null || true

    echo "=== RECOVERY PING ==="
    docker exec "$H1" ping -6 -c 5 -W 1 "$DEST"
}

# Kiem tra trang thai truoc thu nghiem
if docker exec "$R1" ip -6 rule show | grep -q '^10100:'; then
    echo "ERROR: Backup rule already active"
    exit 1
fi

if docker exec "$R1" test -f /tmp/srv6_failover.pid; then
    echo "ERROR: Old Python agent detected"
    exit 1
fi

docker exec "$R1" ip -6 route show table 100 \
    | grep -q "2001:db8:200:5::6" || {
        echo "ERROR: Backup route missing"
        exit 1
    }

trap restore EXIT

echo "=== ACTIVATE BACKUP PATH ==="

docker exec "$R1" ip link set eth1 down

docker exec "$R1" ip -6 rule add \
    pref 10100 \
    from 2001:db8:101::10/128 \
    to 2001:db8:104::10/128 \
    iif eth3 table 100

echo "=== VERIFY BACKUP ==="
docker exec "$R1" ip -6 route get "$DEST" \
    from 2001:db8:101::10 iif eth3

docker exec "$H1" ping -6 -c 3 -W 1 "$DEST"

echo "=== START UDP SERVER ==="
docker exec -d "$H2" \
    iperf3 -s -6 -1 -p "$PORT" -i 1 \
    --logfile /tmp/iperf_failback_server.log

sleep 2

echo "=== START UDP 30 SECONDS ==="

docker exec "$H1" iperf3 -6 -u \
    -c "$DEST" -p "$PORT" \
    -b 20M -l 1200 -t 30 -i 1 \
    > results/udp_failback_only.txt 2>&1 &

UDP_PID=$!

sleep 8

echo "=== TRIGGER FAILBACK ==="

# Khoi phuc lien ket
docker exec "$R1" ip link set eth1 up
docker exec "$R1" ip -6 addr replace \
    2001:db8:12::1/64 dev eth1

sleep 1

# Cai lai duong chinh
docker exec "$R1" ip -6 route replace \
    2001:db8:200:2::1/128 \
    via 2001:db8:12::2 dev eth1

docker exec "$R1" ip -6 route replace \
    "$DEST/128" \
    encap seg6 mode encap \
    segs 2001:db8:200:2::1,2001:db8:200:5::6 \
    via 2001:db8:12::2 dev eth1

# Chuyen tu backup ve primary
docker exec "$R1" ip -6 rule del pref 10100

echo "=== VERIFY PRIMARY ==="

docker exec "$R1" ip -6 route get "$DEST" \
    from 2001:db8:101::10 iif eth3

echo "=== WAIT FOR UDP COMPLETION ==="

wait "$UDP_PID"
echo "=== UDP RECEIVER PER SECOND ==="

docker exec "$H2" \
    cat /tmp/iperf_failback_server.log \
    | tee results/udp_failback_receiver.txt
echo "=== UDP FAILBACK RESULTS ==="

tail -n 12 results/udp_failback_only.txt

echo "=== FIREWALL COUNTERS ==="

docker exec clab-srv6-fw-fw \
    nft list chain ip6 srv6_waypoint transit

echo "=== FAILBACK TEST COMPLETED ==="
