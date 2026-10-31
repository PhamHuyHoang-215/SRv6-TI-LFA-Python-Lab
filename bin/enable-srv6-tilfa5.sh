
#!/usr/bin/env bash
set -euo pipefail

# Lab Containerlab 5 router
PREFIX="clab-srv6-tilfa5"

# Chay lenh trong container
run() {
    docker exec "${PREFIX}-$1" bash -ec "$2"
}

echo "=== 1. ENABLE SRv6 ==="

for r in r1 r2 r3 r4 r5; do
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

echo "=== 2. CONFIGURE SRv6 SID ROUTES ==="

# R2: End SID, tiep tuc chuyen tiep den R4
run r2 '
ip -6 route replace 2001:db8:200:2::1/128 \
encap seg6local action End dev eth2
'

# R4: End.DX6, giai dong goi va chuyen den H2
run r4 '
ip -6 route replace 2001:db8:200:4::1/128 \
encap seg6local action End.DX6 \
nh6 2001:db8:104::10 dev eth3
'

# R5: End SID du kien cho duong sua chua
run r5 '
ip -6 route replace 2001:db8:200:5::1/128 \
encap seg6local action End dev eth2
'

echo "=== 3. CONFIGURE UNDERLAY TO SIDs ==="

# R1 den SID cua R2
run r1 '
ip -6 route replace 2001:db8:200:2::1/128 \
via 2001:db8:12::2 dev eth1
'

# R2 den SID cua R4
run r2 '
ip -6 route replace 2001:db8:200:4::1/128 \
via 2001:db8:24::4 dev eth2
'

# R1 den SID cua R5 qua R3
run r1 '
ip -6 route replace 2001:db8:200:5::1/128 \
via 2001:db8:13::3 dev eth2
'

# R3 den SID cua R5
run r3 '
ip -6 route replace 2001:db8:200:5::1/128 \
via 2001:db8:35::5 dev eth2
'

# R5 den SID cua R4 qua eth2
run r5 '
ip -6 route replace 2001:db8:200:4::1/128 \
via 2001:db8:45::4 dev eth2
'

echo "=== 4. CONFIGURE SRv6 PRIMARY PATH ==="

# Duong chinh: R1 -> R2 -> R4 -> H2
run r1 '
ip -6 route replace 2001:db8:104::/64 \
encap seg6 mode encap \
segs 2001:db8:200:2::1,2001:db8:200:4::1 \
via 2001:db8:12::2 dev eth1
'

echo "=== SRv6 TILFA5 BASELINE CONFIGURED ==="
echo "Primary path: R1 -> R2 -> R4"
echo "R5 SID prepared for future repair tests"
