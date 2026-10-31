#!/usr/bin/env bash
set -euo pipefail
PREFIX=clab-srv6-pylab
printf '=== Nodes ===\n'
sudo containerlab inspect -t topology.clab.yml
printf '\n=== R1 routing ===\n'
docker exec "$PREFIX-r1" ip -6 route
printf '\n=== H1 -> H2 ping ===\n'
docker exec "$PREFIX-h1" ping -6 -c 5 -W 2 2001:db8:104::10
printf '\nOK: basic IPv6 connectivity works. TI-LFA has NOT been enabled.\n'
