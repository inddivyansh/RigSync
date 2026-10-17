import os
import json
import glob
from datetime import datetime, timezone

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}

# NE-07 is Northeast Block 7, NE-08 is Northeast Block 8
ne_areas = ["NE-07", "NE-08"]

print("\n" + "="*50)
print("ANALYZING Q5: Regulator letter spills")
print("="*50)

q5_spills = []

for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json"), "r") as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    if area_id not in ne_areas:
        continue
    
    area_name = area_map[area_id]["name"]
    
    # Check inspections
    insp_file = os.path.join(well_dir, "inspections.jsonl")
    if not os.path.exists(insp_file):
        continue
        
    with open(insp_file, "r", encoding="utf-8") as f:
        for line in f:
            insp = json.loads(line)
            dt_str = insp["inspected_at"]
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            
            # Since 1 Jun 2026
            if dt >= datetime(2026, 6, 1, tzinfo=timezone.utc):
                vol = insp.get("spill_est_volume_bbl")
                # Also check if corrected in context.jsonl
                if insp.get("spill_detected") or (vol is not None and vol > 0):
                    q5_spills.append((wid, area_name, dt, insp))

print(f"Total spills detected in NE-07/NE-08 since 1 Jun 2026: {len(q5_spills)}")

# Now check corrections in context.jsonl and check volume >= 5.0
q5_table = []
for wid, area_name, dt, insp in sorted(q5_spills, key=lambda x: x[2]):
    insp_id = insp["inspection_id"]
    vol = insp.get("spill_est_volume_bbl") or 0.0
    
    # Check if corrected in context.jsonl
    ctx_file = os.path.join(ASSETS_DIR, wid, "context.jsonl")
    correction_note = None
    if os.path.exists(ctx_file):
        with open(ctx_file, "r", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                if c.get("note_type") == "data_correction" and c.get("inspection_id") == insp_id:
                    if c.get("field") == "spill_est_volume_bbl":
                        vol = c.get("corrected_value")
                        correction_note = c
                elif "rainwater" in c.get("text", "").lower() and insp_id in c.get("text", ""):
                    vol = 0.0
                    
    # Only reportable spills (5.0 bbl or more)
    if vol < 5.0:
        continue
        
    # Find clean-up job in maintenance.jsonl
    mnt_file = os.path.join(ASSETS_DIR, wid, "maintenance.jsonl")
    cleanup_job = None
    report_file_path = None
    if os.path.exists(mnt_file):
        with open(mnt_file, "r", encoding="utf-8") as f:
            for line in f:
                mnt = json.loads(line)
                if mnt.get("triggered_by_inspection_id") == insp_id or "spill" in mnt.get("issue", "").lower():
                    # check dates
                    m_start = datetime.fromisoformat(mnt["started_at"].replace("Z", "+00:00"))
                    if m_start >= dt:
                        cleanup_job = mnt["maintenance_id"]
                        report_file = mnt.get("report_file")
                        if report_file:
                            report_file_path = os.path.join(ASSETS_DIR, wid, report_file)
                        break
                        
    # Check report file for "Soil samples sent to the lab."
    has_soil_samples = False
    report_text = ""
    if report_file_path and os.path.exists(report_file_path):
        with open(report_file_path, "r", encoding="utf-8") as rf:
            report_text = rf.read()
            if "soil samples sent to the lab" in report_text.lower():
                has_soil_samples = True
                
    compliant = "Yes" if has_soil_samples else "No"
    reason = "Soil samples sent to lab documented" if has_soil_samples else "Missing lab soil results in clean-up report"
    if not cleanup_job:
        compliant = "No"
        reason = "No clean-up job on record"
        
    q5_table.append({
        "well": wid,
        "area": area_name,
        "inspection": f"{insp_id} ({insp['inspected_at'][:10]})",
        "volume": vol,
        "cleanup_job": cleanup_job or "None",
        "compliant": f"{compliant} ({reason})"
    })

print(f"\nReportable spills covered by regulator's letter: {len(q5_table)}")
for row in q5_table:
    print(f"{row['well']} | {row['area']} | {row['inspection']} | {row['volume']} bbl | {row['cleanup_job']} | {row['compliant']}")

