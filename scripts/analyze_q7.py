import os
import json
import glob
from datetime import datetime, timezone

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")
TODAY = datetime(2027, 1, 15, tzinfo=timezone.utc)
START_WINDOW = datetime(2026, 12, 15, tzinfo=timezone.utc)

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}

keywords = ["sound", "hear", "rattle", "rattling", "squeal", "vibration", "vibrat", "knock", "knocking", "noise", "squeak", "rough", "grind", "grinding", "tripping", "underload", "overload", "slap", "chatter", "chattering"]

q7_candidates = []

for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json")) as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    ctx_file = os.path.join(well_dir, "context.jsonl")
    if not os.path.exists(ctx_file): continue
    
    notes_in_window = []
    with open(ctx_file, "r", encoding="utf-8") as f:
        for line in f:
            n = json.loads(line)
            if n.get("note_type") == "operator_note":
                dt = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00"))
                if START_WINDOW <= dt <= TODAY:
                    txt = n.get("text", "").lower()
                    if any(k in txt for k in keywords):
                        notes_in_window.append((dt, n))
                        
    if not notes_in_window:
        continue
        
    notes_in_window.sort(key=lambda x: x[0])
    latest_abnormal_note = notes_in_window[-1]
    note_dt = latest_abnormal_note[0]
    
    # Check if well had a repair since
    mnt_file = os.path.join(well_dir, "maintenance.jsonl")
    repairs_since = []
    last_repair = None
    all_repairs = []
    if os.path.exists(mnt_file):
        with open(mnt_file, "r", encoding="utf-8") as f:
            for line in f:
                mnt = json.loads(line)
                m_dt = datetime.fromisoformat(mnt["started_at"].replace("Z", "+00:00"))
                all_repairs.append((m_dt, mnt))
                if m_dt > note_dt:
                    repairs_since.append((m_dt, mnt))
                    
    all_repairs.sort(key=lambda x: x[0])
    if all_repairs:
        last_repair = all_repairs[-1][1]
        
    # "Which of those wells haven't had a repair since?"
    if not repairs_since:
        # Check inspections and other warning signs
        insp_file = os.path.join(well_dir, "inspections.jsonl")
        recent_insps = []
        if os.path.exists(insp_file):
            with open(insp_file, "r", encoding="utf-8") as f:
                for line in f:
                    insp = json.loads(line)
                    i_dt = datetime.fromisoformat(insp["inspected_at"].replace("Z", "+00:00"))
                    if i_dt >= datetime(2026, 12, 1, tzinfo=timezone.utc):
                        recent_insps.append(insp)
        recent_insps.sort(key=lambda x: x["inspected_at"])
        
        q7_candidates.append({
            "well": wid,
            "area": area_name,
            "well_type": meta.get("well_type"),
            "note_dt": latest_abnormal_note[1]["created_at"],
            "note_text": latest_abnormal_note[1]["text"],
            "last_repair": f"{last_repair['maintenance_id']} ({last_repair['started_at'][:10]}: {last_repair['issue']})" if last_repair else "None",
            "recent_insps": len(recent_insps),
            "latest_temp_diff": (recent_insps[-1]["wellhead_temp_c"] - recent_insps[-1]["ambient_temp_c"]) if recent_insps else None
        })

print(f"Total wells with abnormal sound/behavior notes in last month without repair since: {len(q7_candidates)}")
for c in q7_candidates:
    print(f"{c['well']} ({c['well_type']}) | {c['area']} | Note: {c['note_dt'][:10]} - \"{c['note_text']}\" | TempDiff: {c['latest_temp_diff']} | LastRepair: {c['last_repair']}")

