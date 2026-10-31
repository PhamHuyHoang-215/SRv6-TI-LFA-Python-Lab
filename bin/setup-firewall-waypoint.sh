
#!/usr/bin/env bash
set -euo pipefail

LAB="clab-srv6-fw"

run() {
    docker exec "${LAB}-$1" sh -ec "$2"
}

echo "=== 1. ENABLE SRv6 ==="

for r in r1 r3 r5; do
    run "$r" '
        sysctl -qw net.ipv6.conf.all.forwarding=1
        sysctl -qw net.ipv6.conf.all.seg6_enabled=1
        sysctl -qw net.ipv6.conf.default.seg6_enabled=1

        for dev in eth1 eth2 eth3 lo; do
            if [ -e "/proc/sys/net/ipv6/conf/$dev/seg6_enabled" ]; then
                sysctl -qw "net.ipv6.conf.$dev.seg6_enabled=1"
            fi
        done
    '
done

echo "=== 2. CONFIGURE FIREWALL NFTABLES ==="

run fw 'sysctl -qw net.ipv6.conf.all.forwarding=1'

# Chi xoa bang firewall rieng cua lab nay
docker exec "${LAB}-fw" nft delete table ip6 srv6_waypoint \
    2>/dev/null || true

docker exec -i "${LAB}-fw" nft -f - <<'NFT'
table ip6 srv6_waypoint {
    chain transit {
        type filter hook forward priority 0;
        policy drop;

        # H1 -> H2
        iifname "eth1" oifname "eth2" \
        ip6 saddr 2001:db8:101::10 \
        ip6 daddr 2001:db8:104::10 \
        counter accept

        # H2 -> H1
        iifname "eth2" oifname "eth1" \
        ip6 saddr 2001:db8:104::10 \
        ip6 daddr 2001:db8:101::10 \
        counter accept
    }
}
NFT

echo "=== 3. CONFIGURE R5 SERVICE SID ==="

# R5 giai dong goi SRv6 va gui IPv6 den Firewall
run r5 '
ip -6 route replace 2001:db8:200:5::6/128 \
encap seg6local action End.DX6 \
nh6 2001:db8:56::6 dev eth3
'

echo "=== 4. CONFIGURE ROUTES TO SERVICE SID ==="

# R3 -> R5 SID
run r3 '
ip -6 route replace 2001:db8:200:5::6/128 \
via 2001:db8:35::5 dev eth2
'

# R1 -> R3 -> R5 SID
run r1 '
ip -6 route replace 2001:db8:200:5::6/128 \
via 2001:db8:13::3 dev eth2
'

echo "=== 5. CONFIGURE SRv6 STEERING ==="

# H1 -> R1 -> R3 -> R5 -> FW -> R4 -> H2
run r1 '
ip -6 route replace 2001:db8:104::10/128 \
encap seg6 mode encap \
segs 2001:db8:200:5::6 \
via 2001:db8:13::3 dev eth2
'

echo "=== 6. CONFIGURE RETURN PATH ==="

# H2 -> R4 -> FW -> R5 -> R3 -> R1 -> H1
run r4 '
ip -6 route replace 2001:db8:101::10/128 \
via 2001:db8:64::6 dev eth4
'

echo "=== FIREWALL WAYPOINT CONFIGURED ==="
echo "Forward: R1 -> R3 -> R5 -> FW -> R4"
echo "Return:  R4 -> FW -> R5 -> R3 -> R1"
echo "Firewall inspection: nftables enabled"
