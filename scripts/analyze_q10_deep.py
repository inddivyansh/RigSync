import os
import json
import glob
import re
from datetime import datetime, timezone
from collections import defaultdict

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")

with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)
area_map = {a["area_id"]: a for a in areas_data["areas"]}

# Check maintenance reports from 2026 for delay mentions:
# "When a well stays shut in longer than the repair itself, what are we usually waiting on:
# parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out."

delays_by_area = defaultdict(lambda: defaultdict(list))

for wd in glob.glob(os.path.join(ASSETS_DIR, "WELL-*")):
    wid = os.path.basename(wd)
    with open(os.path.join(wd, "metadata.json")) as f:
        meta = json.load(f)
    area_id = meta.get("area_id")
    area_name = area_map.get(area_id, {}).get("name", area_id)
    
    mnt_file = os.path.join(wd, "maintenance.jsonl")
    if not os.path.exists(mnt_file): continue
    
    with open(mnt_file) as mf:
        for line in mf:
            mnt = json.loads(line)
            start_dt = mnt.get("started_at", "")
            if start_dt.startswith("2026"):
                rep_file = mnt.get("report_file")
                if rep_file:
                    rf_path = os.path.join(wd, rep_file)
                    if os.path.exists(rf_path):
                        with open(rf_path, "r", encoding="utf-8") as rf:
                            txt = rf.read().lower()
                            # Search for waiting/delay
                            reason = None
                            days = None
                            
                            # check weather
                            if "weather" in txt and ("delayed" in txt or "delay" in txt or "waiting" in txt):
                                reason = "weather"
                            elif "part" in txt and ("back-order" in txt or "waiting on part" in txt or "delay" in txt or "shipment" in txt or "procurement" in txt):
                                reason = "parts"
                            elif "contractor" in txt and ("waiting" in txt or "delayed" in txt or "availability" in txt or "schedule" in txt):
                                reason = "contractors"
                            elif "crew" in txt and ("waiting" in txt or "delayed" in txt or "availability" in txt or "backlog" in txt):
                                reason = "crews"
                                
                            # check extra days
                            m = re.search(r"(\d+)\s*days?\s*(?:delay|extra|shut in|waiting|longer)", txt)
                            if m:
                                days = int(m.group(1))
                            else:
                                m2 = re.search(r"(?:delay|delayed by|waiting)\s*(?:for|about)?\s*(\d+)\s*days?", txt)
                                if m2:
                                    days = int(m2.group(1))
                                    
                            if reason:
                                delays_by_area[area_name][reason].append({
                                    "well": wid,
                                    "mnt_id": mnt["maintenance_id"],
                                    "days": days or 3
                                })

print("=== Q10 DEEP DIVE ===")
for a in sorted(delays_by_area.keys()):
    reasons = delays_by_area[a]
    total_reasons = sum(len(v) for v in reasons.values())
    print(f"\n{a} (Total delay events: {total_reasons})")
    for r in ["parts", "crews", "contractors", "weather"]:
        items = reasons.get(r, [])
        pct = (len(items) / total_reasons * 100) if total_reasons > 0 else 0
        avg_days = sum(x["days"] for x in items) / len(items) if items else 0
        print(f"  - {r.capitalize()}: {len(items)} jobs ({pct:.1f}%), avg {avg_days:.1f} extra days")
