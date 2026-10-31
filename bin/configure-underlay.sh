#!/usr/bin/env bash
set -euo pipefail
PREFIX=clab-srv6-pylab
run() { docker exec "$PREFIX-$1" bash -ec "$2"; }
set_ip() {
  run "$1" "ip link set dev $2 up; ip -6 addr replace $3 dev $2"
}

for r in r1 r2 r3 r4; do
  run "$r" 'sysctl -qw net.ipv6.conf.all.forwarding=1'
done

set_ip h1 eth1 2001:db8:101::10/64
set_ip h2 eth1 2001:db8:104::10/64
set_ip r1 eth1 2001:db8:12::1/64
set_ip r1 eth2 2001:db8:13::1/64
set_ip r1 eth3 2001:db8:101::1/64
set_ip r2 eth1 2001:db8:12::2/64
set_ip r2 eth2 2001:db8:24::2/64
set_ip r3 eth1 2001:db8:13::3/64
set_ip r3 eth2 2001:db8:34::3/64
set_ip r4 eth1 2001:db8:24::4/64
set_ip r4 eth2 2001:db8:34::4/64
set_ip r4 eth3 2001:db8:104::1/64

run h1 'ip -6 route replace default via 2001:db8:101::1 dev eth1'
run h2 'ip -6 route replace default via 2001:db8:104::1 dev eth1'
run r1 'ip -6 route replace 2001:db8:104::/64 via 2001:db8:12::2 dev eth1'
run r2 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:12::1 dev eth1; ip -6 route replace 2001:db8:104::/64 via 2001:db8:24::4 dev eth2'
run r3 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:13::1 dev eth1; ip -6 route replace 2001:db8:104::/64 via 2001:db8:34::4 dev eth2'
run r4 'ip -6 route replace 2001:db8:101::/64 via 2001:db8:24::2 dev eth1'

echo 'Underlay IPv6 configured: primary h1-r1-r2-r4-h2; alternate r1-r3-r4.'
