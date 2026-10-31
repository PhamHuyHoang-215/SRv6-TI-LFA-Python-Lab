#!/usr/bin/env python3
"""Compare three SRv6 lab measurement batches. Python standard library only.

Run from anywhere:
    python3 python/compare_scenarios.py

All outputs go to <project>/results/comparison/.
"""
from __future__ import annotations

import csv
import html
import math
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "comparison"

SCENARIOS = [
    ("normal", "Mang binh thuong", RESULTS / "normal_control"),
    ("plain_failover", "SRv6 + Python failover", None),
    ("fw_failover", "SRv6 + Firewall failover", None),
]


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def available_csvs(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    preferred = folder / "summary.csv"
    if preferred.is_file():
        return [preferred]
    return sorted(folder.glob("*.csv"))


def find_batch(prefix: str) -> Path:
    candidates = sorted(
        (p for p in RESULTS.glob(f"{prefix}*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for folder in candidates:
        for csvfile in available_csvs(folder):
            if has_metrics(csvfile):
                return csvfile
    raise FileNotFoundError(
        f"Khong tim thay CSV co cot loss/gap trong results/{prefix}*/. "
        "Hay kiem tra ten file va cot CSV."
    )


def has_metrics(path: Path) -> bool:
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            header = csv.DictReader(f).fieldnames or []
        names = {normalize(k) for k in header}
        return bool(names & LOSS_FIELDS) and bool(names & GAP_FIELDS) or (
            bool(names & {"sent", "received", "lost"}) and bool(names & GAP_FIELDS)
        )
    except (OSError, UnicodeDecodeError):
        return False


LOSS_FIELDS = {"loss_percent", "packet_loss_percent", "loss_rate", "loss_rate_percent", "loss_pct"}
GAP_FIELDS = {"max_reply_gap_ms", "maximum_reply_gap_ms", "max_gap_ms", "reply_gap_ms"}


def numeric(row: dict[str, str], names: set[str]) -> float | None:
    for key in names:
        value = row.get(key, "")
        if value is None or not value.strip():
            continue
        try:
            result = float(value.replace("%", "").replace(",", "."))
            if math.isfinite(result):
                return result
        except ValueError:
            continue
    return None


def load_metrics(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as f:
        raw = list(csv.DictReader(f))
    if not raw:
        raise ValueError(f"File rong: {path}")

    losses, gaps, sample_sizes, statuses = [], [], [], []
    for index, original in enumerate(raw, start=1):
        row = {normalize(key): (value or "").strip() for key, value in original.items() if key}
        loss = numeric(row, LOSS_FIELDS)
        sent = numeric(row, {"sent", "packets_sent", "transmitted"})
        received = numeric(row, {"received", "packets_received"})
        lost = numeric(row, {"lost", "packets_lost"})
        if loss is None and sent and sent > 0:
            if lost is not None:
                loss = 100 * lost / sent
            elif received is not None:
                loss = 100 * (sent - received) / sent
        gap = numeric(row, GAP_FIELDS)
        if loss is None or gap is None:
            raise ValueError(
                f"{path} dong {index}: thieu loss_percent hoac max_reply_gap_ms. "
                f"Cot: {', '.join(row)}"
            )
        if not (0 <= loss <= 100 and gap >= 0):
            raise ValueError(f"Gia tri khong hop le tai {path} dong {index}")
        losses.append(loss)
        gaps.append(gap)
        if sent is not None:
            sample_sizes.append(int(sent))
        if "status" in row:
            statuses.append(row["status"])

    return {
        "runs": len(raw),
        "loss_mean": statistics.mean(losses),
        "loss_min": min(losses),
        "loss_max": max(losses),
        "gap_mean": statistics.mean(gaps),
        "gap_min": min(gaps),
        "gap_max": max(gaps),
        "sent_values": sorted(set(sample_sizes)),
        "statuses": sorted(set(statuses)),
    }


def svg_bars(rows: list[dict], field: str, title: str, unit: str, filename: str):
    width, height = 960, 350
    left, top, bottom = 100, 70, 80
    plot_height = height - top - bottom
    max_value = max((r[field] for r in rows), default=0)
    scale = max(1.0, max_value * 1.25)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        f'<text x="{left}" y="35" font-family="Arial,sans-serif" font-size="23" font-weight="bold" fill="#1e293b">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top+plot_height}" x2="{width-35}" y2="{top+plot_height}" stroke="#64748b"/>',
    ]
    ticks = 4
    for i in range(ticks + 1):
        value = scale * i / ticks
        y = top + plot_height - plot_height * i / ticks
        lines.extend([
            f'<line x1="{left}" x2="{width-35}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e2e8f0"/>',
            f'<text x="{left-14}" y="{y+5:.1f}" text-anchor="end" font-family="Arial,sans-serif" font-size="13" fill="#475569">{value:.1f}</text>',
        ])
    bar_width, spacing = 150, 115
    for i, row in enumerate(rows):
        x = left + 75 + i * (bar_width + spacing)
        value = row[field]
        bar_h = value * plot_height / scale
        y = top + plot_height - bar_h
        lines.extend([
            f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_h:.2f}" rx="5" fill="#2563eb"/>',
            f'<text x="{x+bar_width/2}" y="{max(top+15,y-10):.1f}" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" font-weight="bold" fill="#0f172a">{value:.2f} {html.escape(unit)}</text>',
            f'<text x="{x+bar_width/2}" y="{height-48}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#1e293b">{html.escape(row["short_label"])}</text>',
        ])
    lines.append('</svg>')
    (OUT / filename).write_text('\n'.join(lines), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {
        "normal": RESULTS / "normal_control" / "summary.csv",
        "plain_failover": find_batch("batch_"),
        "fw_failover": find_batch("fw_continuous_"),
    }
    rows = []
    for key, label, _ in SCENARIOS:
        path = paths[key]
        if not path.exists():
            raise FileNotFoundError(f"Khong tim thay: {path}")
        stats = load_metrics(path)
        rows.append({
            "scenario": key,
            "label": label,
            "short_label": {
                "normal": "Binh thuong",
                "plain_failover": "Failover",
                "fw_failover": "Failover + FW",
            }[key],
            "csv_file": str(path.relative_to(ROOT)),
            **stats,
        })

    print("=== SO SANH BA KICH BAN SRv6 ===")
    print(f'{"Kich ban":<27} {"Runs":>5} {"Loss TB":>11} {"Gap TB":>12} {"Gap Max":>12}')
    print("-" * 75)
    for r in rows:
        print(f'{r["label"]:<27} {r["runs"]:>5} {r["loss_mean"]:>10.2f}% {r["gap_mean"]:>10.2f} ms {r["gap_max"]:>10.2f} ms')
        print("   File:", r["csv_file"])
        if r["runs"] != 10:
            print("   CANH BAO: Khong du 10 lan do")
        if r["sent_values"] and r["sent_values"] != [100]:
            print("   CANH BAO: So goi moi lan do khong dong nhat 100:", r["sent_values"])
        if r["statuses"]:
            print("   Trang thai:", ", ".join(r["statuses"]))

    summary_file = OUT / "comparison.csv"
    with summary_file.open("w", newline="", encoding="utf-8") as f:
        fields = ["scenario", "label", "csv_file", "runs", "loss_mean", "loss_min", "loss_max", "gap_mean", "gap_min", "gap_max"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    svg_bars(rows, "loss_mean", "Ty le mat goi trung binh", "%", "packet_loss.svg")
    svg_bars(rows, "gap_mean", "Khoang cach phan hoi lon nhat - trung binh", "ms", "reply_gap.svg")

    report = [
        "# So sánh ba kịch bản SRv6 - số liệu thực nghiệm",
        "",
        "| Kịch bản | Số lần đo | Mất gói TB | Max reply gap TB | Max reply gap lớn nhất |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        report.append(f'| {r["label"]} | {r["runs"]} | {r["loss_mean"]:.2f}% | {r["gap_mean"]:.2f} ms | {r["gap_max"]:.2f} ms |')
    report += [
        "", "## Nguồn dữ liệu", "",
        *[f'- {r["label"]}: `{r["csv_file"]}`' for r in rows],
        "", "## Giới hạn diễn giải", "",
        "- `max_reply_gap_ms` là khoảng giữa hai phản hồi ICMP liên tiếp; không phải thời gian chuyển mạch TI-LFA.",
        "- Kịch bản thường/không Firewall chạy trên `srv6-tilfa5`; kịch bản Firewall chạy trên `srv6-fw` với topology khác, nên so sánh mang tính tham khảo, chưa phải thí nghiệm cùng một topology với duy nhất biến Firewall.",
        "- Các thí nghiệm sử dụng SRv6 static steering và failover Python; không chứng minh TI-LFA chuẩn RFC 9855 hay bảo vệ dưới 50 ms.",
        "- Kiểm tra độ đồng nhất của chu kỳ ping, số gói, tải VM và tuyến phản hồi trước khi diễn giải khác biệt như tác động Firewall.",
        "", "## Biểu đồ", "", "![Mất gói trung bình](packet_loss.svg)", "", "![Reply gap trung bình](reply_gap.svg)",
    ]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n=== EXPORTED ===")
    for file in (summary_file, OUT / "packet_loss.svg", OUT / "reply_gap.svg", OUT / "report.md"):
        print(file)


if __name__ == "__main__":
    main()
