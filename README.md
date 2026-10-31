# SRv6 + Python TI-LFA Research Lab — Milestone 1

This is a **starter lab**, not a finished TI-LFA implementation. It first checks the Ubuntu/Containerlab network and IPv6 baseline; an optional second script checks Linux SRv6 programmable forwarding. **FRR IS-IS, Python TI-LFA algorithm, local fast repair activation, firewall waypoint and measurements are future milestones.**

## Diagram

```text
                 R2
               /    \
H1 --- R1 ---           --- R4 --- H2
         \      R3    /
          \-----------/
```

Precise links: H1-R1, R1-R2, R1-R3, R2-R4, R3-R4, R4-H2.

## Requirements

- Ubuntu Linux host with Docker and Containerlab already installed
- Kernel supporting `net.ipv6.conf.all.seg6_enabled` and `seg6local` for optional SRv6 step
- Internet access to fetch `ubuntu:24.04` and Ubuntu packages for image build
- Run in the extracted project directory

## Commands

```bash
uname -r
sudo docker info >/dev/null && echo DOCKER_OK
containerlab version
sysctl net.ipv6.conf.all.seg6_enabled

docker build -t srv6-tilfa-base:0.1 .
sudo containerlab deploy -t topology.clab.yml
sudo bash bin/configure-underlay.sh
bash bin/check-underlay.sh
```

If `docker` requires sudo for your user, run `sudo bash bin/configure-underlay.sh` and `sudo bash bin/check-underlay.sh` instead. Docker permission and the `sysctl` output should be checked before deployment. Avoid changing the host's kernel sysctls for this test.

### Optional next step, only after the IPv6 baseline succeeds

```bash
sudo bash bin/enable-srv6.sh
docker exec clab-srv6-pylab-h1 ping -6 -c 5 2001:db8:104::10
```

These are `2001:db8::/32` documentation IPv6 addresses, isolated to the lab.

## IPv6 addressing

| Link | Prefix | Addresses |
|---|---|---|
| H1-R1 | `2001:db8:101::/64` | H1 `::10`, R1 `::1` |
| R1-R2 | `2001:db8:12::/64` | R1 `::1`, R2 `::2` |
| R1-R3 | `2001:db8:13::/64` | R1 `::1`, R3 `::3` |
| R2-R4 | `2001:db8:24::/64` | R2 `::2`, R4 `::4` |
| R3-R4 | `2001:db8:34::/64` | R3 `::3`, R4 `::4` |
| R4-H2 | `2001:db8:104::/64` | R4 `::1`, H2 `::10` |

## Verification and limitations

1. `check-underlay.sh` should return five ICMP echo replies from H2. This only proves basic IPv6 reachability using static routes.
2. `enable-srv6.sh` installs Linux seg6 End, End.DX6 and H.Encaps-style explicit steering to see if the kernel can forward SRv6 packets. This should be verified with route dumps, ping and a packet capture showing Routing Header type 4. It has **not** been runtime-tested on your Ubuntu host, so report any errors verbatim.
3. A TI-LFA claim requires pre-computed and pre-installed protection at the PLR, local fault detection and activation, a valid Repair List per RFC 9855, and instrumentation. A Python script that changes routing after monitoring pings is not enough.
4. Later, IS-IS will be introduced as the IGP and a 6-router topology designed to require a non-empty Repair List and firewall waypoint.

## Cleanup (only this lab)

```bash
sudo containerlab destroy -t topology.clab.yml
```

Do not use `docker system prune -a` or remove other projects.

## References

- https://containerlab.dev/manual/kinds/linux/
- https://containerlab.dev/manual/nodes/
- https://www.rfc-editor.org/rfc/rfc9855.html
- https://www.rfc-editor.org/rfc/rfc8986.html
- https://man7.org/linux/man-pages/man8/ip-route.8.html
