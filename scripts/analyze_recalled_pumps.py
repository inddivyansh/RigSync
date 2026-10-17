import os
import json
import glob
import re

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}
team_map = {t["team_id"]: t for t in areas_data["teams"]}

recalled_lots = ["LOT-2409-A", "LOT-2409-C", "LOT-2410-B"]

print("Scanning all maintenance reports for recalled pumps...")
recalled_pumps = []

for well_dir in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(well_dir)
    with open(os.path.join(well_dir, "metadata.json")) as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    team_id = meta.get("team_id", area_map.get(area_id, {}).get("team_id"))
    
    mnt_file = os.path.join(well_dir, "maintenance.jsonl")
    if not os.path.exists(mnt_file):
        continue
        
    repairs = []
    with open(mnt_file, "r", encoding="utf-8") as f:
        for line in f:
            repairs.append(json.loads(line))
            
    repairs.sort(key=lambda x: x["started_at"])
    
    # Check each repair report
    current_pump = None
    pump_install_history = []
    
    for r in repairs:
        rep_file = r.get("report_file")
        if not rep_file:
            continue
        rf_path = os.path.join(well_dir, rep_file)
        if not os.path.exists(rf_path):
            continue
        with open(rf_path, "r", encoding="utf-8") as rf:
            txt = rf.read()
            # check Parts installed
            if "parts installed" in txt.lower():
                # check for Highline RP-175 and lot numbers
                for lot in recalled_lots:
                    if lot in txt:
                        # Found recalled pump installation!
                        pump_install_history.append({
                            "type": "recalled",
                            "lot": lot,
                            "repair_id": r["maintenance_id"],
                            "date": r["started_at"],
                            "cost": r.get("cost_usd", {}).get("total", 0),
                            "cost_obj": r.get("cost_usd", {})
                        })
                # Check if a non-recalled pump or later pump was installed
                if "downhole pump" in r.get("equipment_kind", "").lower() or "rod pump" in txt.lower() or "pump" in r.get("issue", "").lower():
                    # check if it replaced the pump
                    if any(l in txt for l in ["LOT-2409-B", "LOT-2410-A", "LOT-2410-C", "LOT-2411", "LOT-2412", "LOT-25", "LOT-26"]) or "replaced" in r.get("issue", "").lower():
                        pump_install_history.append({
                            "type": "replacement",
                            "repair_id": r["maintenance_id"],
                            "date": r["started_at"],
                            "issue": r.get("issue")
                        })
                        
    # Check current status of pump in the ground
    if pump_install_history:
        # Check if the latest pump event was recalled
        latest_event = pump_install_history[-1]
        if latest_event["type"] == "recalled":
            # Recalled pump is still in the ground!
            recalled_pumps.append({
                "well": wid,
                "area": area_name,
                "area_id": area_id,
                "team_id": team_id,
                "lot": latest_event["lot"],
                "installed_date": latest_event["date"],
                "repair_id": latest_event["repair_id"],
                "cost_usd": latest_event["cost"]
            })

print(f"Total recalled pumps currently in the ground (before user memory): {len(recalled_pumps)}")
for rp in sorted(recalled_pumps, key=lambda x: x["well"]):
    print(f"{rp['well']} | {rp['area']} ({rp['area_id']}) | Team: {rp['team_id']} | Lot: {rp['lot']} | Installed: {rp['installed_date'][:10]} | Cost: ${rp['cost_usd']:,}")

