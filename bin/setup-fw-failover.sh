#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LAB="clab-srv6-fw"

run() {
    docker exec "${LAB}-$1" sh -ec "$2"
}

echo "=== RESTORE FIREWALL BASELINE ==="

bash bin/configure-underlay-firewall.sh
bash bin/setup-firewall-waypoint.sh

echo "=== CONFIGURE R2-R5 LINK ==="

run r2 '
ip link set eth3 up
ip -6 addr replace 2001:db8:25::2/64 dev eth3
'

run r5 '
ip link set eth4 up
ip -6 addr replace 2001:db8:25::5/64 dev eth4
'

echo "=== ENABLE SRv6 ON R2 ==="

run r2 '
sysctl -qw net.ipv6.conf.all.forwarding=1
sysctl -qw net.ipv6.conf.all.seg6_enabled=1
sysctl -qw net.ipv6.conf.default.seg6_enabled=1
sysctl -qw net.ipv6.conf.eth1.seg6_enabled=1
sysctl -qw net.ipv6.conf.eth3.seg6_enabled=1
'

echo "=== CONFIGURE R2 END SID ==="

run r2 '
ip -6 route replace 2001:db8:200:2::1/128 \
encap seg6local action End dev eth3

ip -6 route replace 2001:db8:200:5::6/128 \
via 2001:db8:25::5 dev eth3
'

echo "=== CONFIGURE R1 PRIMARY ==="

run r1 '
ip -6 route replace 2001:db8:200:2::1/128 \
via 2001:db8:12::2 dev eth1

ip -6 route replace 2001:db8:104::10/128 \
encap seg6 mode encap \
segs 2001:db8:200:2::1,2001:db8:200:5::6 \
via 2001:db8:12::2 dev eth1
'

echo "=== PREINSTALL BACKUP TABLE 100 ==="

run r1 '
ip -6 route replace 2001:db8:104::10/128 \
encap seg6 mode encap \
segs 2001:db8:200:5::6 \
via 2001:db8:13::3 dev eth2 table 100
'

echo "=== ENFORCE NO BYPASS ON R5 ==="

docker exec "${LAB}-r5" \
nft delete table inet bypass_guard 2>/dev/null || true

docker exec -i "${LAB}-r5" nft -f - <<'NFT'
table inet bypass_guard {
    chain forward {
        type filter hook forward priority -10;
        policy accept;

        oifname "eth2" counter drop
    }
}
NFT

echo "=== FIREWALL FAILOVER READY ==="

echo "Primary: R1 -> R2 -> R5 -> FW -> R4"
echo "Backup:  R1 -> R3 -> R5 -> FW -> R4"
echo "Backup table: 100"
echo "Bypass guard: enabled"
