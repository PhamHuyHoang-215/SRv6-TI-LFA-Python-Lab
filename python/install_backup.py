
import json
import subprocess
from pathlib import Path

# Doc Repair Plan da tinh truoc
plan_file = Path(__file__).with_name("repair_plan.json")

with open(plan_file) as f:
    plan = json.load(f)

# Kiem tra thong tin
assert plan["status"] == "PRECOMPUTED"
assert plan["protected_link"] == ["r1", "r2"]
assert plan["backup_next_hop"] == "r3"

# SID R5 duoc lay tu Repair Plan
# SID R4 la SID dich cuoi
segments = plan["repair_list"] + ["2001:db8:200:4::1"]

# Cai san backup route vao table 100 cua R1
command = [
    "docker", "exec", "clab-srv6-tilfa5-r1",
    "ip", "-6", "route", "replace",
    "2001:db8:104::10/128",
    "encap", "seg6",
    "mode", "encap",
    "segs", ",".join(segments),
    "via", "2001:db8:13::3",
    "dev", "eth2",
    "table", "100"
]

subprocess.run(command, check=True)

print("=== SRv6 BACKUP PREINSTALL ===")
print("Protected link: R1-R2")
print("Backup path: R1 -> R3 -> R5 -> R4")
print("Segment List:", segments)
print("Routing table: 100")
print("Status: INSTALLED, NOT ACTIVE")
