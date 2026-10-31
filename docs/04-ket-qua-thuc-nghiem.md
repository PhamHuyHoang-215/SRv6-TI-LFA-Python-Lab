# Chương 4 — Kết quả thực nghiệm SRv6 / Python Failover / Firewall Waypoint

*Tạo tự động: 2026-10-31 11:28 +07*

## 1. Phạm vi

Lab sử dụng Containerlab, Linux, SRv6 và Python. Phần bảo vệ hiện tại là **Python phát hiện lỗi và kích hoạt Policy Routing đã cài sẵn**; chưa chứng minh việc triển khai đầy đủ TI-LFA theo RFC 9855, cũng chưa đo trực tiếp thời gian gián đoạn lưu lượng dưới 50 ms.

## 2. Thực nghiệm ICMPv6 liên tục (100 gói/lần, khoảng gửi danh nghĩa 50 ms)

| Kịch bản | Số lượt có dữ liệu | Mất gói TB | Max reply gap TB | Nguồn |
|---|---:|---:|---:|---|
| Mạng bình thường | 10 | 0.00% | 62.35 ms | `results/normal_control/summary.csv` |
| SRv6 + Python failover | 10 | 1.10% | 107.90 ms | `results/batch_20261030_234548/summary.csv` |
| SRv6 + FW failover | 10 | 1.00% | 111.19 ms | `results/fw_continuous_20261031_012921/summary.csv` |

*Max reply gap là khoảng cách lớn nhất giữa hai phản hồi ICMP liên tiếp, không phải thời gian phục hồi dịch vụ.* Các kịch bản chưa hoàn toàn đồng nhất về topology, không thể quy chênh lệch riêng cho Firewall.

## 3. Đo thời gian thao tác Python Agent khi có Firewall

Nguồn: `results/fw_failover_20261031_011202.csv` (10 lượt có dữ liệu)

| Chỉ tiêu | Trung bình |
|---|---:|
| Phát hiện lỗi (từ lúc bắt đầu thao tác gây lỗi) | 44.365 ms |
| Hoàn tất kích hoạt rule | 47.613 ms |
| Thời gian cài rule | 3.249 ms |

*Đây là thời gian điều khiển, không phải thời gian phục hồi lưu lượng end-to-end.*

## 4. UDP qua Firewall (20 Mbps, 1200 byte/datagram, 30 giây)

| Kịch bản | Mất/Tổng datagram ở receiver | Tỷ lệ mất | File gốc |
|---|---:|---:|---|
| Không có sự cố | 0/62499 | 0.00% | `results/udp_normal_30s.txt` |
| Chỉ failover | 191/62500 | 0.31% | `results/udp_failover_only.txt` |
| Chỉ failback (một lượt) | 2096/62499 | 3.40% | `results/udp_failback_only.txt` |
| Có failover và failback | 4248/62500 | 6.80% | `results/udp_during_failover.txt` |

**Lặp lại failback:** 5 lượt; 10387/312486 datagram mất (3.324%). Nguồn: `results/failback_repeat/summary.csv`.

Các lượt failback có thể dao động đáng kể; tỷ lệ mất UDP tổng cộng không chỉ ra chính xác thời điểm hay nguyên nhân gói mất. Muốn quy kết nguyên nhân cần timestamp tại máy gửi/nhận và kiểm soát chặt kịch bản.

## 5. TCP / UDP ổn định và chính sách Firewall

- TCP với MSS 1200 đã nhận dữ liệu qua Firewall; xem `results/iperf_fw_tcp_mss1200.txt` để trích số liệu sender/receiver và retransmission.
- UDP datagram 1200 byte hoạt động; xem `results/iperf_fw_udp_1200.txt`.
- nftables tại Firewall đã được xác nhận bằng bộ đếm tăng hai chiều.
- Bộ lọc ở R5 đã chặn lưu lượng bypass R5→R4 trong phép thử riêng.
- Vấn đề TCP MSS mặc định / UDP gói lớn cần kiểm tra thêm; chưa kết luận dứt khoát là MTU hay PMTUD.

## 6. Giới hạn và kết luận

Các phép thử chứng minh đường SRv6 chính/dự phòng, Python Agent và đường qua Firewall hoạt động trong những kịch bản được đo. Không thể suy ra cơ chế TI-LFA chuẩn đầy đủ, thời gian phục hồi dịch vụ dưới 50 ms, hay mức bảo vệ cho mọi sự cố.

## 7. Các kết quả có thể mở trực tiếp

- `results/comparison/comparison.csv`
- `results/comparison/packet_loss.svg`
- `results/comparison/reply_gap.svg`
- `results/comparison/report.md`
- `docs/05-danh-muc-minh-chung.md`
