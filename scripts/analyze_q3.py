import os
import json
import glob
import re
from datetime import datetime, timezone

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")
TODAY = datetime(2027, 1, 15, tzinfo=timezone.utc)

# 1. Load fleet metadata
with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}
team_map = {t["team_id"]: t for t in areas_data["teams"]}

with open(os.path.join(FLEET_DIR, "users.json"), "r") as f:
    users_data = json.load(f)
user_map = {u["user_id"]: u for u in users_data["users"]}

# Map well to area and team
well_meta = {}
for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json"), "r") as f:
        well_meta[wid] = json.load(f)

print(f"Loaded metadata for {len(well_meta)} wells.")

# -------------------------------------------------------------
# Q3: Gas reports since 1 Nov 2026
# -------------------------------------------------------------
print("\n" + "="*50)
print("ANALYZING Q3: Gas reports since 1 Nov 2026")
print("="*50)

# OPS-1: operator note reporting gas smell (smelled gas, rotten-egg smell, gas odor, H2S monitor alarmed).
# Field response: maintenance job started_at, or inspection with method == 'manual' (drone doesn't count).
# Must start after note's created_at and within:
# - 24 hours for reports noted before 1 Jan 2027
# - 12 hours for reports noted from 1 Jan 2027
gas_keywords = ["gas smell", "rotten-egg", "rotten egg", "gas odor", "odor of gas", "h2s monitor alarmed", "h2s alarm", "smelled gas"]

q3_reports = []
for wid, meta in well_meta.items():
    well_dir = os.path.join(ASSETS_DIR, wid)
    ctx_file = os.path.join(well_dir, "context.jsonl")
    if not os.path.exists(ctx_file):
        continue
    
    with open(ctx_file, "r", encoding="utf-8") as f:
        for line in f:
            note = json.loads(line)
            if note.get("note_type") == "operator_note":
                created_at_str = note["created_at"]
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if dt >= datetime(2026, 11, 1, tzinfo=timezone.utc):
                    text = note["text"].lower()
                    if any(k in text for k in gas_keywords):
                        q3_reports.append((wid, dt, note))

print(f"Total gas odor notes since 1 Nov 2026: {len(q3_reports)}")

q3_table = []
for wid, dt, note in sorted(q3_reports, key=lambda x: x[1]):
    well_dir = os.path.join(ASSETS_DIR, wid)
    area_id = well_meta[wid].get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    deadline_hrs = 24 if dt < datetime(2027, 1, 1, tzinfo=timezone.utc) else 12
    
    # Check responses: maintenance jobs or manual inspections after dt
    responses = []
    
    mnt_file = os.path.join(well_dir, "maintenance.jsonl")
    if os.path.exists(mnt_file):
        with open(mnt_file, "r", encoding="utf-8") as f:
            for line in f:
                mnt = json.loads(line)
                mnt_start = datetime.fromisoformat(mnt["started_at"].replace("Z", "+00:00"))
                if mnt_start > dt:
                    diff_hrs = (mnt_start - dt).total_seconds() / 3600.0
                    responses.append((diff_hrs, mnt["maintenance_id"], mnt["started_at"], "maintenance"))
                    
    insp_file = os.path.join(well_dir, "inspections.jsonl")
    if os.path.exists(insp_file):
        with open(insp_file, "r", encoding="utf-8") as f:
            for line in f:
                insp = json.loads(line)
                if insp.get("method") == "manual":
                    insp_dt = datetime.fromisoformat(insp["inspected_at"].replace("Z", "+00:00"))
                    if insp_dt > dt:
                        diff_hrs = (insp_dt - dt).total_seconds() / 3600.0
                        responses.append((diff_hrs, insp["inspection_id"], insp["inspected_at"], "manual_inspection"))
                        
    responses.sort(key=lambda x: x[0])
    if responses:
        best_resp = responses[0]
        hrs = best_resp[0]
        rec_id = f"{best_resp[1]} ({best_resp[2]})"
        met = "Met" if hrs <= deadline_hrs else "Missed"
    else:
        hrs = None
        rec_id = "None"
        met = "Missed"
        
    q3_table.append({
        "well": wid,
        "area": area_name,
        "reported_at": note["created_at"],
        "text": note["text"],
        "response": rec_id,
        "hours": round(hrs, 1) if hrs is not None else "N/A",
        "deadline": f"{deadline_hrs}h",
        "status": met
    })

print(f"Q3 Table Entries: {len(q3_table)}")
for row in q3_table:
    print(f"{row['well']} | {row['area']} | {row['reported_at']} | {row['response']} | {row['hours']} | {row['deadline']} | {row['status']}")

