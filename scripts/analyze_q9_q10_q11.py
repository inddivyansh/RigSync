import os
import json
import glob
import re
from datetime import datetime, timezone
from collections import defaultdict

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")
TODAY = datetime(2027, 1, 15, tzinfo=timezone.utc)

# 1. Northwest Production details (Q9 turn 2)
with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}
team_map = {t["team_id"]: t for t in areas_data["teams"]}

with open(os.path.join(FLEET_DIR, "users.json"), "r") as f:
    users_data = json.load(f)
user_map = {u["user_id"]: u for u in users_data["users"]}

print("=== Q9 TURN 2: Northwest Production ===")
nw_team = team_map.get("TEAM-NW")
print("NW Team:", nw_team)
if nw_team:
    lead_user = user_map.get(nw_team["lead_user_id"])
    print("Lead User:", lead_user)

# Count wells run by TEAM-NW
nw_wells = []
for wd in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    # Check well's team_id or team_history
    t_id = meta.get("team_id")
    if not t_id:
        t_id = area_map.get(meta.get("area_id"), {}).get("team_id")
    if t_id == "TEAM-NW":
        nw_wells.append(wid)
print(f"Total wells run by Northwest Production: {len(nw_wells)}")

# 2. Cold weather checks in Dec 2026 (Q9 turn 3)
print("\n=== Q9 TURN 3: Cold weather checks in Dec 2026 ===")
# OPS-5 Freeze protection (1 Dec - 28 Feb): inspection with ambient_temp_c <= -5 C on a well producing oil at that reading
# needs a heat trace check (maintenance job with issue containing "Heat trace check") starting within 7 days.
thresh = {"T200": 15.0, "T350": 20.0, "T500": 25.0}
cold_inspections = []
missed_heat_checks = []

for wd in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    wtype = meta.get("well_type", "T200")
    th = thresh.get(wtype, 15.0)
    
    insp_file = os.path.join(wd, "inspections.jsonl")
    if not os.path.exists(insp_file): continue
    
    with open(insp_file) as f:
        for line in f:
            insp = json.loads(line)
            dt = datetime.fromisoformat(insp["inspected_at"].replace("Z", "+00:00"))
            if datetime(2026, 12, 1, tzinfo=timezone.utc) <= dt <= datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc):
                if insp["ambient_temp_c"] is not None and insp["ambient_temp_c"] <= -5.0:
                    diff = insp["wellhead_temp_c"] - insp["ambient_temp_c"]
                    if diff >= th:
                        cold_inspections.append((wid, dt, insp))
                        # Check maintenance jobs within 7 days
                        mnt_file = os.path.join(wd, "maintenance.jsonl")
                        has_heat_check = False
                        if os.path.exists(mnt_file):
                            with open(mnt_file) as mf:
                                for mline in mf:
                                    mnt = json.loads(mline)
                                    if "heat trace check" in mnt.get("issue", "").lower():
                                        m_dt = datetime.fromisoformat(mnt["started_at"].replace("Z", "+00:00"))
                                        diff_days = (m_dt - dt).total_seconds() / 86400.0
                                        if 0 <= diff_days <= 7.0:
                                            has_heat_check = True
                                            break
                        if not has_heat_check:
                            missed_heat_checks.append((wid, insp["inspected_at"], insp["ambient_temp_c"], diff))

print(f"Cold inspections (<= -5 C and producing) in Dec 2026: {len(cold_inspections)}")
print(f"Missed heat trace checks: {len(missed_heat_checks)}")
for m in missed_heat_checks[:10]:
    print(f"  {m[0]} on {m[1]} (Ambient: {m[2]} C, Diff: {m[3]:.1f} C)")

# 3. Production status right now of the 9 recalled pump wells (Q9 turn 5)
print("\n=== Q9 TURN 5: Status right now of 9 recalled pump wells ===")
recalled_wells = ["WELL-0031", "WELL-0156", "WELL-0160", "WELL-0263", "WELL-0305", "WELL-0333", "WELL-0426", "WELL-0428", "WELL-0577"]
for wid in recalled_wells:
    wd = os.path.join(ASSETS_DIR, wid)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    wtype = meta.get("well_type", "T200")
    th = thresh.get(wtype, 15.0)
    
    with open(os.path.join(wd, "inspections.jsonl")) as f:
        insps = [json.loads(line) for line in f]
    insps.sort(key=lambda x: x["inspected_at"])
    latest_insp = insps[-1]
    diff = latest_insp["wellhead_temp_c"] - latest_insp["ambient_temp_c"]
    insp_prod = (diff >= th)
    
    # check last repair
    with open(os.path.join(wd, "maintenance.jsonl")) as f:
        mnts = [json.loads(line) for line in f]
    mnts.sort(key=lambda x: x["started_at"])
    last_mnt = mnts[-1] if mnts else None
    
    print(f"{wid} ({wtype}): Latest Insp {latest_insp['inspected_at'][:10]} Diff {diff:.1f} C (th {th} C) -> {'PRODUCING' if insp_prod else 'NOT PRODUCING'} | Last Repair: {last_mnt['maintenance_id'] if last_mnt else 'None'} ({last_mnt['started_at'][:10] if last_mnt else ''}: {last_mnt['issue'] if last_mnt else ''})")

# 4. Q10: Waiting reasons by area for jobs started in 2026
print("\n=== Q10: Waiting reasons by area for jobs started in 2026 ===")
# Michael Turner: "When a well stays shut in longer than the repair itself, what are we usually waiting on:
# parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out."

# Let's inspect context.jsonl notes or maintenance reports for waiting reasons!
waiting_notes = defaultdict(lambda: defaultdict(list))
for wd in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    ctx_file = os.path.join(wd, "context.jsonl")
    if os.path.exists(ctx_file):
        with open(ctx_file) as f:
            for line in f:
                n = json.loads(line)
                txt = n.get("text", "").lower()
                dt_str = n.get("created_at", "")
                if dt_str.startswith("2026"):
                    # Check waiting reason
                    reason = None
                    if "part" in txt: reason = "parts"
                    elif "crew" in txt: reason = "crews"
                    elif "contractor" in txt: reason = "contractors"
                    elif "weather" in txt: reason = "weather"
                    
                    if reason:
                        # Extract days if mentioned
                        match = re.search(r"(\d+)\s*day", txt)
                        days = int(match.group(1)) if match else None
                        waiting_notes[area_name][reason].append((wid, txt, days))

print("Waiting notes breakdown by area:")
for a, reasons in waiting_notes.items():
    print(f"\nArea: {a}")
    for r, items in reasons.items():
        print(f"  {r}: {len(items)} notes, e.g. {items[0][1]}")

# 5. Q11: Which region runs hotter?
print("\n=== Q11: Regional temperatures ===")
area_temps = defaultdict(list)
area_ambient = defaultdict(list)
area_wellhead = defaultdict(list)

for wd in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    insp_file = os.path.join(wd, "inspections.jsonl")
    if os.path.exists(insp_file):
        with open(insp_file) as f:
            for line in f:
                insp = json.loads(line)
                if insp["wellhead_temp_c"] is not None:
                    area_wellhead[area_name].append(insp["wellhead_temp_c"])
                if insp["ambient_temp_c"] is not None:
                    area_ambient[area_name].append(insp["ambient_temp_c"])
                if insp["wellhead_temp_c"] is not None and insp["ambient_temp_c"] is not None:
                    area_temps[area_name].append(insp["wellhead_temp_c"] - insp["ambient_temp_c"])

for a in sorted(area_wellhead.keys()):
    avg_wh = sum(area_wellhead[a]) / len(area_wellhead[a])
    avg_amb = sum(area_ambient[a]) / len(area_ambient[a])
    avg_diff = sum(area_temps[a]) / len(area_temps[a])
    print(f"{a}: Avg Wellhead = {avg_wh:.2f} °C, Avg Ambient = {avg_amb:.2f} °C, Avg Diff = {avg_diff:.2f} °C (Inspections: {len(area_wellhead[a])})")
