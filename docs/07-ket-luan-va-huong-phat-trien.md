# KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 1. Kết quả đạt được

Dự án đã xây dựng môi trường mô phỏng mạng
SRv6 bằng Docker và Containerlab.

Đã triển khai:
- Thuật toán Dijkstra, P-space, Q-space, PQ-node.
- Tính toán Repair List bằng Python.
- Cài sẵn đường dự phòng SRv6.
- Python Agent tự động phát hiện lỗi và chuyển tuyến.
- Firewall Waypoint bằng Linux nftables.
- Chính sách ngăn lưu lượng bypass Firewall.
- Kiểm thử ICMPv6, TCP, UDP, Failover và Failback.
- Thu thập dữ liệu CSV và biểu đồ thực nghiệm.

## 2. Kết quả thực nghiệm chính

### ICMPv6

- Mạng bình thường: 0% packet loss.
- Python Failover: 1.10% packet loss trung bình.
- Firewall Failover: 1.00% packet loss trung bình.

### Firewall Failover

- 10/10 lần kiểm thử thành công.
- Phát hiện lỗi trung bình: 44.365 ms.
- Kích hoạt dự phòng trung bình: 47.613 ms.
- Cài rule trung bình: 3.249 ms.

### UDP 20 Mbps

- Không sự cố: 0% packet loss.
- Failover only: 0.31% packet loss.
- Failback only (5 lần): 3.324% packet loss.
- Failover và Failback: 6.8% packet loss.

Các kết quả cho thấy việc chuyển tuyến và khôi phục
có ảnh hưởng đến chất lượng truyền dữ liệu.

## 3. Giới hạn

Dự án hiện là mô hình SRv6 và cơ chế
Python-based failover.

Chưa triển khai đầy đủ TI-LFA theo RFC 9855.

Chưa chứng minh thời gian phục hồi dịch vụ
end-to-end dưới 50 ms.

Một số kịch bản sử dụng topology khác nhau.
Nguyên nhân mất gói khi Failback cần được
nghiên cứu thêm.

## 4. Hướng phát triển

- Tích hợp IS-IS và cơ sở dữ liệu link-state.
- Tự động tính lại Repair List khi topology thay đổi.
- Triển khai và xác minh TI-LFA theo RFC 9855.
- Đo thời gian phục hồi lưu lượng chính xác hơn.
- Tối ưu quá trình Failback.
- Đánh giá nhiều mức tải và nhiều kiểu sự cố.
- Mở rộng kiểm thử ràng buộc Service Function.

## 5. Kết luận

Kết quả thực nghiệm chứng minh tính khả thi
của việc kết hợp tính toán đường sửa chữa bằng
Python, chuyển tiếp SRv6 và Firewall Waypoint.

Dự án là nền tảng để tiếp tục nghiên cứu và
triển khai cơ chế TI-LFA đầy đủ.
