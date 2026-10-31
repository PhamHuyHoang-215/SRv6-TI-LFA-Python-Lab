#!/usr/bin/env python3
"""Generate SRv6 lab experiment report and evidence index from existing results.

Run: python3 python/build_experiment_report.py
Standard library only. Does not modify network state or run experiments.
"""
from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def latest_complete(pattern: str, minimum: int = 10) -> tuple[Path | None, list[dict[str, str]]]:
    for path in sorted(RESULTS.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True):
        rows = load_csv(path)
        if len(rows) >= minimum:
            return path, rows
    return None, []


def numeric_mean(rows: list[dict[str, str]], key: str) -> float | None:
    vals = []
    for row in rows:
        try:
            vals.append(float(row[key]))
        except (KeyError, TypeError, ValueError):
            continue
    return mean(vals) if vals else None


def fmt(value: float | None, unit: str = "", digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}{unit}"


def relative(path: Path | None) -> str:
    return path.relative_to(ROOT).as_posix() if path else "Không tìm thấy"


def iperf_udp(path: Path) -> tuple[int, int, float] | None:
    if not path.is_file():
        return None
    data = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"(\d+)\s*/\s*(\d+)\s*\(([\d.]+)%\)\s+receiver\b", data)
    if not matches:
        return None
    lost, total, pct = matches[-1]
    return int(lost), int(total), float(pct)


normal_path = RESULTS / "normal_control/summary.csv"
normal = load_csv(normal_path)
no_fw_path, no_fw = latest_complete("batch_*/summary.csv")
fw_path, fw = latest_complete("fw_continuous_*/summary.csv")
ctrl_path, ctrl = latest_complete("fw_failover_*.csv")
back_path = RESULTS / "failback_repeat/summary.csv"
back = load_csv(back_path)

scenarios = [
    ("Mạng bình thường", normal_path, normal),
    ("SRv6 + Python failover", no_fw_path, no_fw),
    ("SRv6 + FW failover", fw_path, fw),
]

lines = [
    "# Chương 4 — Kết quả thực nghiệm SRv6 / Python Failover / Firewall Waypoint",
    "",
    f"*Tạo tự động: {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}*",
    "",
    "## 1. Phạm vi",
    "",
    "Lab sử dụng Containerlab, Linux, SRv6 và Python. Phần bảo vệ hiện tại là "
    "**Python phát hiện lỗi và kích hoạt Policy Routing đã cài sẵn**; "
    "chưa chứng minh việc triển khai đầy đủ TI-LFA theo RFC 9855, "
    "cũng chưa đo trực tiếp thời gian gián đoạn lưu lượng dưới 50 ms.",
    "",
    "## 2. Thực nghiệm ICMPv6 liên tục (100 gói/lần, khoảng gửi danh nghĩa 50 ms)",
    "",
    "| Kịch bản | Số lượt có dữ liệu | Mất gói TB | Max reply gap TB | Nguồn |",
    "|---|---:|---:|---:|---|",
]
for label, path, rows in scenarios:
    lines.append(
        f"| {label} | {len(rows)} | {fmt(numeric_mean(rows, 'loss_percent'), '%')} "
        f"| {fmt(numeric_mean(rows, 'max_reply_gap_ms'), ' ms')} | `{relative(path)}` |"
    )
lines += [
    "",
    "*Max reply gap là khoảng cách lớn nhất giữa hai phản hồi ICMP liên tiếp, "
    "không phải thời gian phục hồi dịch vụ.* Các kịch bản chưa hoàn toàn đồng nhất về topology, "
    "không thể quy chênh lệch riêng cho Firewall.",
    "",
    "## 3. Đo thời gian thao tác Python Agent khi có Firewall",
    "",
    f"Nguồn: `{relative(ctrl_path)}` ({len(ctrl)} lượt có dữ liệu)",
    "",
    "| Chỉ tiêu | Trung bình |",
    "|---|---:|",
    f"| Phát hiện lỗi (từ lúc bắt đầu thao tác gây lỗi) | {fmt(numeric_mean(ctrl, 'detection_interval_ms'), ' ms', 3)} |",
    f"| Hoàn tất kích hoạt rule | {fmt(numeric_mean(ctrl, 'activation_interval_ms'), ' ms', 3)} |",
    f"| Thời gian cài rule | {fmt(numeric_mean(ctrl, 'rule_install_ms'), ' ms', 3)} |",
    "",
    "*Đây là thời gian điều khiển, không phải thời gian phục hồi lưu lượng end-to-end.*",
    "",
    "## 4. UDP qua Firewall (20 Mbps, 1200 byte/datagram, 30 giây)",
    "",
    "| Kịch bản | Mất/Tổng datagram ở receiver | Tỷ lệ mất | File gốc |",
    "|---|---:|---:|---|",
]
for label, filename in [
    ("Không có sự cố", "udp_normal_30s.txt"),
    ("Chỉ failover", "udp_failover_only.txt"),
    ("Chỉ failback (một lượt)", "udp_failback_only.txt"),
    ("Có failover và failback", "udp_during_failover.txt"),
]:
    path = RESULTS / filename
    measurement = iperf_udp(path)
    if measurement:
        lost, total, pct = measurement
        value, percent = f"{lost}/{total}", f"{pct:.2f}%"
    else:
        value, percent = "N/A", "N/A"
    lines.append(f"| {label} | {value} | {percent} | `{relative(path)}` |")

if back:
    try:
        lost = sum(int(float(row["lost"])) for row in back)
        total = sum(int(float(row["total"])) for row in back)
        rate = lost / total * 100 if total else None
        lines.extend([
            "",
            f"**Lặp lại failback:** {len(back)} lượt; {lost}/{total} datagram mất "
            f"({fmt(rate, '%', 3)}). Nguồn: `{relative(back_path)}`."
        ])
    except (ValueError, KeyError):
        lines.append("\nKhông phân tích được CSV lặp lại failback; cần kiểm tra các cột lost và total.")

lines += [
    "",
    "Các lượt failback có thể dao động đáng kể; tỷ lệ mất UDP tổng cộng không chỉ ra chính xác "
    "thời điểm hay nguyên nhân gói mất. Muốn quy kết nguyên nhân cần timestamp tại máy gửi/nhận "
    "và kiểm soát chặt kịch bản.",
    "",
    "## 5. TCP / UDP ổn định và chính sách Firewall",
    "",
    "- TCP với MSS 1200 đã nhận dữ liệu qua Firewall; "
    "xem `results/iperf_fw_tcp_mss1200.txt` để trích số liệu sender/receiver và retransmission.",
    "- UDP datagram 1200 byte hoạt động; xem `results/iperf_fw_udp_1200.txt`.",
    "- nftables tại Firewall đã được xác nhận bằng bộ đếm tăng hai chiều.",
    "- Bộ lọc ở R5 đã chặn lưu lượng bypass R5→R4 trong phép thử riêng.",
    "- Vấn đề TCP MSS mặc định / UDP gói lớn cần kiểm tra thêm; chưa kết luận dứt khoát là MTU hay PMTUD.",
    "",
    "## 6. Giới hạn và kết luận",
    "",
    "Các phép thử chứng minh đường SRv6 chính/dự phòng, Python Agent và đường qua Firewall hoạt động "
    "trong những kịch bản được đo. Không thể suy ra cơ chế TI-LFA chuẩn đầy đủ, "
    "thời gian phục hồi dịch vụ dưới 50 ms, hay mức bảo vệ cho mọi sự cố.",
    "",
    "## 7. Các kết quả có thể mở trực tiếp",
    "",
    "- `results/comparison/comparison.csv`",
    "- `results/comparison/packet_loss.svg`",
    "- `results/comparison/reply_gap.svg`",
    "- `results/comparison/report.md`",
    "- `docs/05-danh-muc-minh-chung.md`",
    "",
]

report_path = DOCS / "04-ket-qua-thuc-nghiem.md"
report_path.write_text("\n".join(lines), encoding="utf-8")

# Curated index of measurement evidence, not data duplication.
evidence = [
    normal_path, no_fw_path, fw_path, ctrl_path, back_path,
    RESULTS / "comparison/comparison.csv",
    RESULTS / "comparison/packet_loss.svg",
    RESULTS / "comparison/reply_gap.svg",
    RESULTS / "comparison/report.md",
    *[RESULTS / n for n in (
        "udp_normal_30s.txt", "udp_failover_only.txt", "udp_failback_only.txt",
        "udp_during_failover.txt", "iperf_fw_tcp_mss1200.txt", "iperf_fw_udp_1200.txt",
    )],
]
index = ["# Danh mục minh chứng", "", "File có tồn tại mới được tính là minh chứng đã lưu.", "",
         "| File | Kích thước | SHA256 (12 ký tự đầu) |", "|---|---:|---|"]
missing = []
for path in evidence:
    if path is None or not path.is_file():
        missing.append(relative(path))
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    index.append(f"| `{relative(path)}` | {path.stat().st_size:,} byte | `{digest}` |")
index.extend(["", "## Còn thiếu / cần xác minh", ""])
index.extend(f"- `{path}`" for path in missing) if missing else index.append("Không có file thiếu trong danh mục đã định.")
index_path = DOCS / "05-danh-muc-minh-chung.md"
index_path.write_text("\n".join(index) + "\n", encoding="utf-8")

print("=== EXPERIMENT REPORT EXPORTED ===")
for p in (report_path, index_path):
    print(p.relative_to(ROOT))
print("Scenario runs:", *(f"{label}={len(rows)}" for label, _, rows in scenarios), sep=" | ")
print("Failback repeat runs:", len(back))
print("Missing evidence files:", len(missing))
for item in missing:
    print("  -", item)
print("NEXT: Review docs/*.md and compare against raw logs.")
