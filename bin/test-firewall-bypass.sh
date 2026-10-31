
#!/usr/bin/env bash
set -Eeuo pipefail

R1="clab-srv6-fw-r1"
R3="clab-srv6-fw-r3"
R5="clab-srv6-fw-r5"
FW="clab-srv6-fw-fw"
H1="clab-srv6-fw-h1"

DEST="2001:db8:104::10"

# Khoi phuc duong SRv6 qua Firewall khi ket thuc
restore_waypoint() {
    trap - EXIT
    set +e

    echo
    echo "=== RESTORE FIREWALL WAYPOINT ==="

    docker exec "$R3" ip -6 route del \
      "$DEST/128" 2>/dev/null

    docker exec "$R1" ip -6 route replace \
      "$DEST/128" \
      encap seg6 mode encap \
      segs 2001:db8:200:5::6 \
      via 2001:db8:13::3 dev eth2

    echo "=== TEST WAYPOINT AFTER RESTORE ==="
    docker exec "$H1" ping -6 -c 5 -W 1 "$DEST"

    echo "=== FIREWALL COUNTERS ==="
    docker exec "$FW" \
      nft list chain ip6 srv6_waypoint transit

    echo "=== BYPASS GUARD ==="
    docker exec "$R5" \
      nft list table inet bypass_guard

    echo "=== TEST FINISHED ==="
}

trap restore_waypoint EXIT

echo "=== 1. REMOVE OLD TEST GUARD ==="

# Chi tac dong den bang bao ve cua lab thu nghiem
docker exec "$R5" \
  nft delete table inet bypass_guard 2>/dev/null || true

echo "=== 2. FIREWALL COUNTERS BEFORE ==="

docker exec "$FW" \
  nft list chain ip6 srv6_waypoint transit

echo "=== 3. FORCE DIRECT BYPASS ==="

# R1 -> R3
docker exec "$R1" ip -6 route replace \
  "$DEST/128" \
  via 2001:db8:13::3 dev eth2

# R3 -> R5; R5 da co duong IPv6 den R4
docker exec "$R3" ip -6 route replace \
  "$DEST/128" \
  via 2001:db8:35::5 dev eth2

echo "=== 4. TEST BYPASS BEFORE BLOCK ==="

docker exec "$H1" ping -6 -c 5 -W 1 "$DEST"

echo "=== 5. FIREWALL COUNTERS AFTER BYPASS ==="

docker exec "$FW" \
  nft list chain ip6 srv6_waypoint transit

echo "=== 6. INSTALL BYPASS PROTECTION ==="

# Chan tat ca goi forwarded di ra R5 eth2 -> R4
docker exec -i "$R5" nft -f - <<'NFT'
table inet bypass_guard {
    chain forward {
        type filter hook forward priority -10;
        policy accept;

        oifname "eth2" counter drop
    }
}
NFT

echo "=== 7. TEST BYPASS AFTER BLOCK ==="

if docker exec "$H1" ping -6 -c 5 -W 1 "$DEST"; then
    echo "FAIL: DIRECT BYPASS STILL WORKS"
else
    echo "EXPECTED: DIRECT BYPASS BLOCKED"
fi

echo "=== 8. CHECK DROPPED PACKETS ==="

docker exec "$R5" \
  nft list chain inet bypass_guard forward

echo "=== 9. RESTORE AND VERIFY WAYPOINT ==="
