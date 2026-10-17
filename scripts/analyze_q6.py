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

# Production threshold by well type:
# T200: >= 15 C above ambient
# T350: >= 20 C above ambient
# T500: >= 25 C above ambient
thresh_map = {"T200": 15.0, "T350": 20.0, "T500": 25.0}

print("\n" + "="*50)
print("ANALYZING Q6: Latest inspection vs operator notes disagreements")
print("="*50)

q6_disagreements = []

for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json"), "r") as f:
        meta = json.load(f)
        
    well_type = meta.get("well_type", "T200")
    threshold = thresh_map.get(well_type, 15.0)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    # 1. Get all inspections
    insp_file = os.path.join(well_dir, "inspections.jsonl")
    if not os.path.exists(insp_file):
        continue
        
    inspections = []
    with open(insp_file, "r", encoding="utf-8") as f:
        for line in f:
            inspections.append(json.loads(line))
            
    if not inspections:
        continue
        
    # Sort inspections by date (accounting for late-entered records)
    inspections.sort(key=lambda x: x["inspected_at"])
    latest_insp = inspections[-1]
    
    # Check data correction for latest inspection
    ctx_file = os.path.join(well_dir, "context.jsonl")
    corrections = {}
    notes = []
    if os.path.exists(ctx_file):
        with open(ctx_file, "r", encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                if c.get("note_type") == "data_correction":
                    if c.get("inspection_id") == latest_insp["inspection_id"]:
                        corrections[c.get("field")] = c.get("corrected_value")
                elif c.get("note_type") == "operator_note":
                    notes.append(c)
                    
    # Thermal difference
    w_temp = corrections.get("wellhead_temp_c", latest_insp.get("wellhead_temp_c"))
    a_temp = corrections.get("ambient_temp_c", latest_insp.get("ambient_temp_c"))
    diff = w_temp - a_temp if (w_temp is not None and a_temp is not None) else None
    insp_producing = (diff is not None and diff >= threshold)
    
    # 2. Check operator notes about shut-in or restart
    # "saying the well was shut in or restarted"
    shut_restart_notes = []
    for n in notes:
        txt = n.get("text", "").lower()
        if any(w in txt for w in ["shut in", "shut-in", "restarted", "back online", "brought back"]):
            shut_restart_notes.append(n)
            
    if not shut_restart_notes:
        continue
        
    shut_restart_notes.sort(key=lambda x: x["created_at"])
    latest_note = shut_restart_notes[-1]
    
    insp_dt = latest_insp["inspected_at"]
    note_dt = latest_note["created_at"]
    note_txt = latest_note.get("text", "").lower()
    
    is_shut = any(w in note_txt for w in ["shut in", "shut-in"])
    is_restart = any(w in note_txt for w in ["restarted", "back online", "brought back"])
    
    # Disagreement cases:
    # Case 1: Latest inspection shows producing, but operator note (more recent or not) says shut in
    # Case 2: Latest inspection shows NOT producing, but operator note says restarted/back online
    disagreement = False
    status_now = None
    reason = None
    
    if note_dt > insp_dt:
        # Note is newer than inspection!
        if insp_producing and is_shut:
            disagreement = True
            status_now = "Not producing oil"
            reason = f"Shut-in note on {note_dt[:10]} is more recent than inspection on {insp_dt[:10]} (OPS-3)"
        elif (not insp_producing) and is_restart:
            disagreement = True
            status_now = "Producing oil (unconfirmed)"
            reason = f"Restart note on {note_dt[:10]} is more recent than inspection on {insp_dt[:10]} (OPS-3 unconfirmed until next inspection)"
    else:
        # Inspection is newer than note!
        # If note was shut-in, but inspection shows producing -> inspection superseded note, producing oil.
        # If note was restart, but inspection shows NOT producing -> inspection found well not producing.
        # But Nathan asked: "for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?"
        # Let's check both possibilities!
        if insp_producing and is_shut:
            # Inspection says producing, but note said shut-in without a restart note
            disagreement = True
            status_now = "Producing oil"
            reason = f"Inspection on {insp_dt[:10]} confirmed producing ({diff:.1f} °C above air >= {threshold} °C), superseding older shut-in note on {note_dt[:10]}"
        elif (not insp_producing) and is_restart:
            disagreement = True
            status_now = "Not producing oil"
            reason = f"Inspection on {insp_dt[:10]} showed well not producing ({diff:.1f} °C above air < {threshold} °C), superseding older restart note on {note_dt[:10]}"
            
    if disagreement:
        q6_disagreements.append({
            "well": wid,
            "area": area_name,
            "insp_id": latest_insp["inspection_id"],
            "insp_date": insp_dt,
            "insp_shows": f"{'Producing' if insp_producing else 'Not producing'} ({diff:.1f} °C diff, threshold {threshold} °C)",
            "note_date": note_dt,
            "note_says": latest_note["text"],
            "status_now": status_now,
            "reason": reason,
            "note_is_newer": note_dt > insp_dt
        })

print(f"Total disagreements found: {len(q6_disagreements)}")
for d in sorted(q6_disagreements, key=lambda x: x["well"]):
    print(f"\n{d['well']} | {d['area']}")
    print(f"  Inspection: {d['insp_id']} ({d['insp_date']}) -> {d['insp_shows']}")
    print(f"  Operator Note: ({d['note_date']}) -> {d['note_says']}")
    print(f"  Status Now: {d['status_now']} | Reason: {d['reason']}")

