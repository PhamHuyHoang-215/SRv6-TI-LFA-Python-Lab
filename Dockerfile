FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    iproute2 iputils-ping iperf3 tcpdump nftables procps python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
