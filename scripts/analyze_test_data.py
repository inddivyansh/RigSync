import os
import json
import glob
from datetime import datetime, timezone
from collections import defaultdict, Counter

DATA_DIR = r"c:\Users\divya\DataDrive\Study\Projects\FlytLabs_MLH\RigSync\test-data\dataset"
ASSETS_DIR = os.path.join(DATA_DIR, "assets")
FLEET_DIR = os.path.join(DATA_DIR, "fleet")

print("Checking dataset files...")

# Load areas and users
with open(os.path.join(FLEET_DIR, "areas.json"), "r") as f:
    areas_data = json.load(f)

with open(os.path.join(FLEET_DIR, "users.json"), "r") as f:
    users_data = json.load(f)

print(f"Areas: {len(areas_data['areas'])}, Teams: {len(areas_data['teams'])}, Users: {len(users_data['users'])}")

# Check Q1: Pressure data in any file?
pressure_matches = []
well_dirs = glob.glob(os.path.join(ASSETS_DIR, "WELL-*"))
print(f"Found {len(well_dirs)} well directories.")

sample_insp_fields = set()
for wd in well_dirs[:50]:
    insp_file = os.path.join(wd, "inspections.jsonl")
    if os.path.exists(insp_file):
        with open(insp_file, "r") as f:
            for i, line in enumerate(f):
                obj = json.loads(line)
                sample_insp_fields.update(obj.keys())
                for k, v in obj.items():
                    if "press" in str(k).lower() or (isinstance(v, str) and "press" in v.lower()):
                        pressure_matches.append((obj["asset_id"], k, v))
                if i > 50:
                    break

print("Inspection fields found:", sample_insp_fields)
print(f"Direct pressure matches in first 50 wells inspections: {len(pressure_matches)}")

# Check Q2: Production volume data?
prod_matches = []
for wd in well_dirs[:50]:
    insp_file = os.path.join(wd, "inspections.jsonl")
    if os.path.exists(insp_file):
        with open(insp_file, "r") as f:
            for i, line in enumerate(f):
                obj = json.loads(line)
                for k, v in obj.items():
                    if "prod" in str(k).lower() or "bopd" in str(k).lower() or "volume" in str(k).lower() and k != "spill_est_volume_bbl":
                        prod_matches.append((obj["asset_id"], k, v))
                if i > 50:
                    break
print(f"Production volume fields found in first 50 wells: {prod_matches}")
