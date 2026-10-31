#!/usr/bin/env bash
# Optional second milestone: SRv6 segment steering over the primary r1-r2-r4 path.
# Not TI-LFA. Run only AFTER check-underlay.sh succeeds.
set -euo pipefail
PREFIX=clab-srv6-pylab
run() { docker exec "$PREFIX-$1" bash -ec "$2"; }
for r in r1 r2 r3 r4; do
  run "$r" 'sysctl -qw net.ipv6.conf.all.seg6_enabled=1; sysctl -qw net.ipv6.conf.default.seg6_enabled=1; for dev in lo eth1 eth2 eth3; do if [ -e "/proc/sys/net/ipv6/conf/$dev/seg6_enabled" ]; then sysctl -qw "net.ipv6.conf.$dev.seg6_enabled=1"; fi; done'
done

# On R2, consume the intermediate SID; on R4, decapsulate and send the inner IPv6 packet to H2.
run r2 'ip -6 route replace 2001:db8:200:2::1/128 encap seg6local action End dev eth2'
run r2 'ip -6 route replace 2001:db8:200:4::1/128 via 2001:db8:24::4 dev eth2'
run r4 'ip -6 route replace 2001:db8:200:4::1/128 encap seg6local action End.DX6 nh6 2001:db8:104::10 dev eth3'

run r1 'ip -6 route replace 2001:db8:200:2::1/128 via 2001:db8:12::2 dev eth1'
# Prefix steering at headend R1: first R2 (End), then R4 (End.DX6).
run r1 'ip -6 route replace 2001:db8:104::/64 encap seg6 mode encap segs 2001:db8:200:2::1,2001:db8:200:4::1 via 2001:db8:12::2 dev eth1'

echo 'Installed static SRv6 steering. Test with:'
echo "  docker exec $PREFIX-h1 ping -6 -c 5 2001:db8:104::10"
echo "  docker exec $PREFIX-r1 ip -6 route show 2001:db8:104::/64"
echo "  docker exec $PREFIX-r2 ip -6 route show 2001:db8:200:2::1/128"
echo 'This is NOT TI-LFA, nor a full RFC 9256 SR Policy.'
