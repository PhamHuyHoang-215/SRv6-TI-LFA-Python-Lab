# RÀ SOÁT PHẠM VI KỸ THUẬT SRv6 + PYTHON FAILOVER

## 1. Các thành phần đã triển khai

- Mô hình mạng Linux bằng Docker và Containerlab.
- Chuyển tiếp SRv6 với các SID End và End.DX6.
- Thuật toán Dijkstra, P-space, Q-space và PQ-node trên Python.
- Tính toán Repair List và Repair Plan.
- Cài sẵn đường dự phòng trong Linux Routing Table 100.
- Python Agent phát hiện sự cố liên kết R1-R2.
- Kích hoạt đường dự phòng bằng Linux Policy Routing.
- Firewall Waypoint sử dụng nftables.
- Chặn đường bypass R5-R4 trong mô hình thử nghiệm.
- Kiểm thử ICMPv6, TCP, UDP, Failover và Failback.

## 2. Kết quả thực nghiệm

### ICMPv6 - 10 lần thử mỗi kịch bản

| Kịch bản | Packet Loss TB | Max Reply Gap TB |
|---|---:|---:|
| Mạng bình thường | 0% | 62.35 ms |
| Python Failover | 1.10% | 107.90 ms |
| Firewall Failover | 1.00% | 111.19 ms |

### Firewall Failover - 10 lần thử

- Thành công: 10/10 lần.
- Thời gian phát hiện trung bình: 44.365 ms.
- Thời gian kích hoạt trung bình: 47.613 ms.
- Thời gian cài rule trung bình: 3.249 ms.

### UDP - 20 Mbps, datagram 1200 bytes

| Kịch bản | Packet Loss |
|---|---:|
| Bình thường, 30 giây | 0% |
| Chỉ Failover | 0.31% |
| Chỉ Failback, 5 lần | 3.324% |
| Failover và Failback | 6.8% |

### TCP

- TCP với MSS 1200: 861 Mbit/s ở một lần thử.
- UDP bình thường: 20 Mbit/s, 0% loss.

## 3. Giới hạn nghiên cứu

- Chưa triển khai đầy đủ TI-LFA theo RFC 9855.
- Chưa tích hợp IGP link-state để tự động tính và cập nhật Repair List.
- Các tuyến SRv6 hiện chủ yếu được cấu hình tĩnh.
- Phát hiện lỗi sử dụng Python Agent và trạng thái interface.
- Chưa chứng minh thời gian phục hồi dịch vụ dưới 50 ms.
- Một số phép đo thực hiện trên các topology khác nhau.
- Thuật toán cần được đánh giá lại trên topology Firewall mở rộng.
- Chưa xác định đầy đủ nguyên nhân mất gói trong quá trình Failback.

## 4. Kết luận phạm vi

Dự án xây dựng và kiểm thử mô hình SRv6 với cơ chế
tính toán đường sửa chữa và chuyển tuyến bằng Python.

Kết quả chứng minh tính khả thi của việc sử dụng
Repair List, SRv6 và Firewall Waypoint trong lab.

Không đồng nhất cơ chế Python Failover hiện tại
với một triển khai TI-LFA chuẩn RFC 9855.

## 5. Tài liệu tham khảo

RFC 9855 - Topology Independent Fast Reroute
Using Segment Routing.

https://www.rfc-editor.org/rfc/rfc9855.html
