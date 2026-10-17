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

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}
team_map = {t["team_id"]: t for t in areas_data["teams"]}

with open(os.path.join(FLEET_DIR, "users.json"), "r") as f:
    users_data = json.load(f)
user_map = {u["user_id"]: u for u in users_data["users"]}

well_meta = {}
for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json"), "r") as f:
        well_meta[wid] = json.load(f)

# -------------------------------------------------------------
# Q4: Temporary flowline bypasses
# -------------------------------------------------------------
print("\n" + "="*50)
print("ANALYZING Q4: Temporary flowline bypasses")
print("="*50)

# MOC-2026-031: WELL-0013, WELL-0062, WELL-0118, WELL-0248, WELL-0476. Expired 30 Nov 2026.
# Extended by MOC-2026-044 to 28 Feb 2027.
# MOC-2026-036: WELL-0087, WELL-0158, WELL-0249, WELL-0284, WELL-0356, WELL-0388, WELL-0461. Expired 15 Dec 2026.

# Let's search all operator notes for bypass
bypass_wells = defaultdict(list)
for wid in well_meta.keys():
    ctx_file = os.path.join(ASSETS_DIR, wid, "context.jsonl")
    if os.path.exists(ctx_file):
        with open(ctx_file, "r", encoding="utf-8") as f:
            for line in f:
                note = json.loads(line)
                if "bypass" in note.get("text", "").lower():
                    bypass_wells[wid].append(note)

print(f"Wells with bypass notes: {len(bypass_wells)}")
q4_results = []
for wid, notes in bypass_wells.items():
    area_id = well_meta[wid].get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    notes.sort(key=lambda x: x["created_at"])
    
    # Determine in/out
    in_date = None
    out_date = None
    for n in notes:
        txt = n["text"].lower()
        if "temporary bypass installed" in txt or "bypass installed" in txt or "put in" in txt or "routed" in txt or "bypass in" in txt:
            in_date = n["created_at"][:10]
        if "bypass removed" in txt or "taken out" in txt or "bypass out" in txt or "removed bypass" in txt:
            out_date = n["created_at"][:10]
            
    # Check approvals
    # MOC-2026-031 / 044
    moc31_wells = ["WELL-0013", "WELL-0062", "WELL-0118", "WELL-0248", "WELL-0476"]
    moc36_wells = ["WELL-0087", "WELL-0158", "WELL-0249", "WELL-0284", "WELL-0356", "WELL-0388", "WELL-0461"]
    
    approval = "None"
    valid_until = "None"
    status = "Not approved"
    
    if wid in moc31_wells:
        approval = "MOC-2026-044 (ext. MOC-2026-031)"
        valid_until = "2027-02-28"
        if out_date:
            status = "Allowed (removed)"
        else:
            status = "Allowed"
    elif wid in moc36_wells:
        approval = "MOC-2026-036"
        valid_until = "2026-12-15"
        if out_date:
            if out_date <= "2026-12-15":
                status = "Allowed (removed on time)"
            else:
                status = "Expired before removal"
        else:
            status = "Expired"
    else:
        status = "Not approved"
        
    q4_results.append({
        "well": wid,
        "area": area_name,
        "bypass_in": in_date or notes[0]["created_at"][:10],
        "bypass_out": out_date or "still in",
        "approval": approval,
        "valid_until": valid_until,
        "status": status,
        "notes": [n["text"] for n in notes]
    })

print(f"Total Q4 bypass entries: {len(q4_results)}")
for r in sorted(q4_results, key=lambda x: x["well"]):
    print(f"{r['well']} | {r['area']} | In: {r['bypass_in']} | Out: {r['bypass_out']} | {r['approval']} | Valid: {r['valid_until']} | Status: {r['status']}")
    print(f"   Notes: {r['notes']}")

