import json
import glob
import os
from datetime import datetime, timezone

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}

thresh = {"T200": 15.0, "T350": 20.0, "T500": 25.0}

print("=== Q6: ALL INSTANCES WHERE OPERATOR NOTE IS NEWER THAN LATEST INSPECTION ===")
for wd in sorted(glob.glob(os.path.join(ASSETS_DIR, "WELL-*"))):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    wtype = meta.get("well_type", "T200")
    th = thresh.get(wtype, 15.0)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    insp_file = os.path.join(wd, "inspections.jsonl")
    if not os.path.exists(insp_file): continue
    with open(insp_file) as f:
        insps = [json.loads(line) for line in f]
    if not insps: continue
    insps.sort(key=lambda x: x["inspected_at"])
    latest_insp = insps[-1]
    
    # check corrections
    ctx_file = os.path.join(wd, "context.jsonl")
    if not os.path.exists(ctx_file): continue
    with open(ctx_file) as f:
        ctx_lines = [json.loads(line) for line in f]
        
    corrections = {c.get("field"): c.get("corrected_value") for c in ctx_lines if c.get("note_type") == "data_correction" and c.get("inspection_id") == latest_insp["inspection_id"]}
    w_temp = corrections.get("wellhead_temp_c", latest_insp.get("wellhead_temp_c"))
    a_temp = corrections.get("ambient_temp_c", latest_insp.get("ambient_temp_c"))
    diff = w_temp - a_temp
    insp_prod = (diff >= th)
    
    notes = [c for c in ctx_lines if c.get("note_type") == "operator_note"]
    shut_restart = [n for n in notes if any(w in n.get("text", "").lower() for w in ["shut in", "shut-in", "restarted", "back online", "brought back"])]
    if not shut_restart: continue
    shut_restart.sort(key=lambda x: x["created_at"])
    latest_note = shut_restart[-1]
    
    insp_dt = latest_insp["inspected_at"]
    note_dt = latest_note["created_at"]
    txt = latest_note.get("text", "").lower()
    note_shut = ("shut in" in txt or "shut-in" in txt)
    note_restart = any(w in txt for w in ["restarted", "back online", "brought back"])
    
    # Disagreement:
    # If note is newer:
    if note_dt > insp_dt:
        if (insp_prod and note_shut) or ((not insp_prod) and note_restart):
            status_now = "Not producing oil (shut in)" if note_shut else "Producing oil (unconfirmed)"
            print(f"{wid} | {area_name}")
            print(f"  Latest Insp: {latest_insp['inspection_id']} ({insp_dt}) -> {'Producing' if insp_prod else 'Not producing'} ({diff:.1f} C diff, th {th} C)")
            print(f"  Latest Note: ({note_dt}) -> {latest_note['text']}")
            print(f"  Status Now: {status_now}\n")
    # Also if inspection is within last week (Jan 2027) and note is within last week (Jan 2027) but insp was newer:
    elif note_dt >= "2027-01-01":
        if (insp_prod and note_shut) or ((not insp_prod) and note_restart):
            status_now = "Producing oil" if insp_prod else "Not producing oil"
            print(f"{wid} [Insp newer, but both in Jan 2027] | {area_name}")
            print(f"  Latest Insp: {latest_insp['inspection_id']} ({insp_dt}) -> {'Producing' if insp_prod else 'Not producing'} ({diff:.1f} C diff, th {th} C)")
            print(f"  Latest Note: ({note_dt}) -> {latest_note['text']}")
            print(f"  Status Now: {status_now}\n")
