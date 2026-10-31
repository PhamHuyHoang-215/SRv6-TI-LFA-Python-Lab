
#!/usr/bin/env bash
set -euo pipefail

# Ten lab Containerlab 5 router
PREFIX="clab-srv6-fw"

# Thuc thi lenh trong container
run() {
    docker exec "$PREFIX-$1" bash -ec "$2"
}

# Gan dia chi IPv6 cho interface
set_ip() {
    run "$1" "ip link set dev $2 up; ip -6 addr replace $3 dev $2"
}

echo "=== BAT IPv6 FORWARDING ==="

for r in r1 r2 r3 r4 r5; do
    run "$r" "sysctl -qw net.ipv6.conf.all.forwarding=1"
done

echo "=== CAU HINH IPV6 ==="

# Host
set_ip h1 eth1 2001:db8:101::10/64
set_ip h2 eth1 2001:db8:104::10/64

# Router R1
set_ip r1 eth1 2001:db8:12::1/64
set_ip r1 eth2 2001:db8:13::1/64
set_ip r1 eth3 2001:db8:101::1/64

# Router R2
set_ip r2 eth1 2001:db8:12::2/64
set_ip r2 eth2 2001:db8:24::2/64

# Router R3
set_ip r3 eth1 2001:db8:13::3/64
set_ip r3 eth2 2001:db8:35::3/64

# Router R4
set_ip r4 eth1 2001:db8:24::4/64
set_ip r4 eth2 2001:db8:45::4/64
set_ip r4 eth3 2001:db8:104::1/64

# Router R5
set_ip r5 eth1 2001:db8:35::5/64
set_ip r5 eth2 2001:db8:45::5/64

echo "=== CAU HINH DINH TUYEN TINH ==="

# Default gateway cho Host
run h1 'ip -6 route replace default via 2001:db8:101::1 dev eth1'
run h2 'ip -6 route replace default via 2001:db8:104::1 dev eth1'

# R1: duong chinh di qua R2
run r1 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:12::2 dev eth1'

# R2
run r2 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:12::1 dev eth1'
run r2 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:24::4 dev eth2'

# R3: truoc su co, duong den H2 di qua R1
run r3 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:13::1 dev eth1'
run r3 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:13::1 dev eth1'

# R5
run r5 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:35::3 dev eth1'
run r5 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:45::4 dev eth2'

# R4
run r4 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:24::2 dev eth1'

echo "=== IPV6 UNDERLAY TILFA5 CONFIGURED ==="

echo "=== CONFIGURE FIREWALL LINKS ==="

# R5 - Firewall
set_ip r5 eth3 2001:db8:56::5/64
set_ip fw eth1 2001:db8:56::6/64

# Firewall - R4
set_ip fw eth2 2001:db8:64::6/64
set_ip r4 eth4 2001:db8:64::4/64

# Bat IPv6 forwarding tren Firewall
run fw 'sysctl -qw net.ipv6.conf.all.forwarding=1'

# Firewall den mang H2 qua R4
run fw 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:64::4 dev eth2'

# Firewall den mang H1 qua R5
run fw 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:56::5 dev eth1'

echo "=== FIREWALL UNDERLAY CONFIGURED ==="
