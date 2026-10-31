# Mô phỏng SRv6 Fast Reroute và Firewall Waypoint bằng Python

## 1. Giới thiệu

Dự án nghiên cứu và mô phỏng cơ chế bảo vệ đường đi
trong mạng Segment Routing over IPv6 (SRv6).

Hệ thống sử dụng Python để tính toán đường dự phòng,
chuẩn bị Repair List và kích hoạt chuyển tuyến khi
phát hiện sự cố liên kết.

Dự án đồng thời tích hợp Firewall Waypoint để kiểm tra
khả năng duy trì ràng buộc đường đi khi xảy ra sự cố.

**Phạm vi:** Đây là mô hình SRv6 với Python-based
failover, không phải triển khai TI-LFA đầy đủ theo
RFC 9855.

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Môi trường | Ubuntu, Docker |
| Mô phỏng mạng | Containerlab |
| Chuyển tiếp | Linux IPv6, SRv6 |
| Thuật toán | Python, Dijkstra |
| Tính đường sửa chữa | P-space, Q-space, PQ-node |
| Firewall | Linux nftables |
| Failover | Python Agent, Linux Policy Routing |
| Đo kiểm | ping, iperf3, tcpdump |
| Phân tích | Python, CSV, SVG |

## 3. Kiến trúc mạng

Topology Firewall có 5 router, 2 host và 1 Firewall.

Đường chính:

H1 → R1 → R2 → R5 → FW → R4 → H2

Đường dự phòng:

H1 → R1 → R3 → R5 → FW → R4 → H2

Một liên kết trực tiếp R5–R4 được giữ lại để thử
nghiệm khả năng chặn lưu lượng bypass Firewall.

### Cơ chế chuyển tuyến

- R1 giám sát trạng thái liên kết đến R2.
- Python Agent phát hiện khi interface bị down.
- Đường dự phòng SRv6 được cài trước trong table 100.
- Linux Policy Routing kích hoạt đường dự phòng.
- SID End.DX6 tại R5 đưa lưu lượng vào Firewall.
- nftables kiểm tra, cho phép hoặc chặn lưu lượng.

## 4. Cấu trúc dự án

- `bin/`: Script Bash cấu hình và kiểm thử.
- `python/`: Thuật toán và chương trình failover.
- `docs/`: Tài liệu kỹ thuật và kết quả nghiên cứu.
- `results/`: CSV, biểu đồ và báo cáo.
- `Dockerfile`: Image Linux phục vụ mô phỏng.
- `topology.clab.yml`: Topology SRv6 ban đầu.
- `topology-tilfa5.clab.yml`: Topology 5 router.
- `topology-firewall.clab.yml`: Topology có Firewall.

## 5. Hướng dẫn triển khai

### Yêu cầu

Ubuntu với Docker, Containerlab, Python 3,
Linux hỗ trợ SRv6 và các quyền chạy container.

### Bước 1: Build Docker image

```bash
sudo docker build -t srv6-tilfa-base:0.1 .
```

### Bước 2: Khởi tạo topology

```bash
sudo containerlab deploy -t topology-firewall.clab.yml
```

### Bước 3: Cấu hình Firewall Failover

```bash
sudo bash bin/setup-fw-failover.sh
```

Script thiết lập IPv6, SRv6, đường chính, bảng
dự phòng và chính sách chặn bypass.

### Bước 4: Kiểm tra kết nối

```bash
sudo docker exec clab-srv6-fw-h1 \
  ping -6 -c 5 2001:db8:104::10
```

### Bước 5: Kiểm tra Firewall

```bash
sudo docker exec clab-srv6-fw-fw \
  nft list chain ip6 srv6_waypoint transit
```

### Bước 6: Phân tích dữ liệu

```bash
python3 python/compare_scenarios.py
python3 python/build_experiment_report.py
```

Các bài thử gây sự cố phải được chạy có kiểm soát,
theo hướng dẫn trong `bin/` và `python/`.

## 6. Kết quả thực nghiệm

### ICMPv6

| Kịch bản | Mất gói TB | Max Reply Gap TB |
|---|---:|---:|
| Mạng bình thường | 0% | 62.35 ms |
| Python Failover | 1.10% | 107.90 ms |
| Firewall Failover | 1.00% | 111.19 ms |

Mỗi kịch bản được đo 10 lần.

### Firewall Failover

Qua 10 phép thử:

- Thời gian phát hiện trung bình: 44.365 ms.
- Thời gian kích hoạt trung bình: 47.613 ms.
- Thời gian cài rule trung bình: 3.249 ms.

Các giá trị này là thời gian xử lý điều khiển,
không phải thời gian phục hồi dịch vụ end-to-end.

### UDP ở mức tải 20 Mbps

| Kịch bản | Packet Loss |
|---|---:|
| Không có sự cố | 0% |
| Chỉ Failover | 0.31% |
| Chỉ Failback, 5 lần | 3.324% |
| Failover và Failback | 6.8% |

UDP sử dụng datagram 1200 byte và thời lượng
30 giây mỗi phép thử.

### TCP

Thông lượng TCP với MSS 1200 đạt 861 Mbit/s
trong một lần thử nghiệm.

## 7. Giới hạn

- Chưa triển khai đầy đủ TI-LFA theo RFC 9855.
- Chưa tích hợp IGP link-state để tự động cập nhật
  Repair List trên mạng thực.
- Chưa chứng minh phục hồi dịch vụ dưới 50 ms.
- Một số kết quả so sánh sử dụng topology khác nhau.
- Chưa xác định đầy đủ nguyên nhân mất gói Failback.

## 8. Tài liệu và minh chứng

- `docs/04-ket-qua-thuc-nghiem.md`
- `docs/05-danh-muc-minh-chung.md`
- `docs/06-pham-vi-ky-thuat.md`
- `results/comparison/`

## 9. Tài liệu tham khảo

- RFC 8986: SRv6 Network Programming.
- RFC 9256: Segment Routing Policy Architecture.
- RFC 9855: TI-LFA Using Segment Routing.

## 10. Kết luận

Dự án chứng minh tính khả thi của việc kết hợp
thuật toán tính đường sửa chữa bằng Python,
chuyển tiếp SRv6 và Firewall Waypoint trong
môi trường mô phỏng Containerlab.

Kết quả cho thấy có thể chuyển tuyến dự phòng
và duy trì lưu lượng qua Firewall trong các
kịch bản kiểm thử, đồng thời ghi nhận tác động
của Failover và Failback đến hiệu năng.
